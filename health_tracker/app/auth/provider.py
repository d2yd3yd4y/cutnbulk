from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol
from uuid import uuid4

from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import UserProfile
from app.security.passwords import hash_password, verify_password


@dataclass
class AuthResult:
    user_id: str
    email: str
    access_token: str | None = None
    refresh_token: str | None = None
    expires_at: object | None = None
    needs_email_verification: bool = False
    message: str | None = None


class AuthError(Exception):
    def __init__(self, message: str):
        self.message = message
        super().__init__(message)


class AuthProvider(Protocol):
    def register(self, db: Session, email: str, password: str) -> AuthResult: ...

    def login(self, db: Session, email: str, password: str) -> AuthResult: ...

    def request_password_reset(self, email: str) -> None: ...

    def update_password(self, access_token: str, new_password: str) -> None: ...

    def refresh(self, refresh_token: str) -> AuthResult: ...

    def exchange_recovery_session(self, access_token: str, refresh_token: str) -> AuthResult: ...


class LocalAuthProvider:
    """Development/testing auth that stores bcrypt hashes in user_profiles."""

    def register(self, db: Session, email: str, password: str) -> AuthResult:
        email = email.strip().lower()
        existing = db.query(UserProfile).filter(UserProfile.email == email).first()
        if existing:
            raise AuthError("该邮箱已注册，请直接登录。")
        user = UserProfile(
            id=str(uuid4()),
            email=email,
            password_hash=hash_password(password),
            onboarding_completed=False,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return AuthResult(user_id=user.id, email=user.email, access_token="local", refresh_token="local")

    def login(self, db: Session, email: str, password: str) -> AuthResult:
        email = email.strip().lower()
        user = db.query(UserProfile).filter(UserProfile.email == email).first()
        if not user or not verify_password(password, user.password_hash):
            raise AuthError("邮箱或密码不正确。")
        return AuthResult(user_id=user.id, email=user.email, access_token="local", refresh_token="local")

    def request_password_reset(self, email: str) -> None:
        # Uniform response handled by caller; local mode no-ops mail delivery.
        return None

    def update_password(self, access_token: str, new_password: str) -> None:
        raise AuthError("本地模式请直接联系管理员重置，或使用开发注册账号。")

    def refresh(self, refresh_token: str) -> AuthResult:
        raise AuthError("本地会话无需刷新。")

    def exchange_recovery_session(self, access_token: str, refresh_token: str) -> AuthResult:
        raise AuthError("本地模式不支持邮件重置回调。")


class SupabaseAuthProvider:
    def __init__(self) -> None:
        settings = get_settings()
        if not settings.supabase_url or not settings.supabase_publishable_key:
            raise RuntimeError("Supabase Auth 未配置完整。")
        from supabase import create_client

        self._client = create_client(settings.supabase_url, settings.supabase_publishable_key)
        self._admin = None
        if settings.supabase_service_role_key:
            self._admin = create_client(settings.supabase_url, settings.supabase_service_role_key)

    def register(self, db: Session, email: str, password: str) -> AuthResult:
        email = email.strip().lower()
        try:
            response = self._client.auth.sign_up(
                {
                    "email": email,
                    "password": password,
                    "options": {
                        "email_redirect_to": f"{get_settings().app_base_url}/auth/callback",
                    },
                }
            )
        except Exception as exc:  # noqa: BLE001
            message = str(exc)
            if "already" in message.lower() or "registered" in message.lower():
                raise AuthError("该邮箱已注册，请直接登录。") from exc
            raise AuthError("注册失败，请稍后重试。") from exc

        user = response.user
        if user is None:
            raise AuthError("注册失败，请稍后重试。")

        profile = db.query(UserProfile).filter(UserProfile.id == user.id).first()
        if profile is None:
            profile = UserProfile(id=str(user.id), email=email, onboarding_completed=False)
            db.add(profile)
            db.commit()

        session = response.session
        needs_verify = session is None
        return AuthResult(
            user_id=str(user.id),
            email=email,
            access_token=session.access_token if session else None,
            refresh_token=session.refresh_token if session else None,
            expires_at=None,
            needs_email_verification=needs_verify,
            message="注册成功，请查收验证邮件后再登录。" if needs_verify else None,
        )

    def login(self, db: Session, email: str, password: str) -> AuthResult:
        email = email.strip().lower()
        try:
            response = self._client.auth.sign_in_with_password(
                {"email": email, "password": password}
            )
        except Exception as exc:  # noqa: BLE001
            message = str(exc).lower()
            if "email not confirmed" in message or "not confirmed" in message:
                raise AuthError("请先完成邮箱验证，再登录。") from exc
            raise AuthError("邮箱或密码不正确。") from exc

        user = response.user
        session = response.session
        if user is None or session is None:
            raise AuthError("登录失败，请稍后重试。")

        profile = db.query(UserProfile).filter(UserProfile.id == str(user.id)).first()
        if profile is None:
            profile = UserProfile(
                id=str(user.id),
                email=email,
                onboarding_completed=False,
            )
            db.add(profile)
            db.commit()
        elif profile.email != email:
            profile.email = email
            db.commit()

        return AuthResult(
            user_id=str(user.id),
            email=email,
            access_token=session.access_token,
            refresh_token=session.refresh_token,
        )

    def request_password_reset(self, email: str) -> None:
        try:
            self._client.auth.reset_password_email(
                email.strip().lower(),
                {
                    "redirect_to": f"{get_settings().app_base_url}/auth/reset-password",
                },
            )
        except Exception:
            # Uniform UX: never reveal whether the email exists.
            return None

    def update_password(self, access_token: str, new_password: str) -> None:
        try:
            self._client.auth.set_session(access_token, access_token)
            self._client.auth.update_user({"password": new_password})
        except Exception as exc:  # noqa: BLE001
            raise AuthError("重置链接无效或已过期，请重新申请。") from exc

    def refresh(self, refresh_token: str) -> AuthResult:
        try:
            response = self._client.auth.refresh_session(refresh_token)
        except Exception as exc:  # noqa: BLE001
            raise AuthError("登录已过期，请重新登录。") from exc
        user = response.user
        session = response.session
        if user is None or session is None:
            raise AuthError("登录已过期，请重新登录。")
        return AuthResult(
            user_id=str(user.id),
            email=user.email or "",
            access_token=session.access_token,
            refresh_token=session.refresh_token,
        )

    def exchange_recovery_session(self, access_token: str, refresh_token: str) -> AuthResult:
        try:
            self._client.auth.set_session(access_token, refresh_token)
            user_response = self._client.auth.get_user(access_token)
            user = user_response.user
        except Exception as exc:  # noqa: BLE001
            raise AuthError("重置链接无效或已过期，请重新申请。") from exc
        if user is None:
            raise AuthError("重置链接无效或已过期，请重新申请。")
        return AuthResult(
            user_id=str(user.id),
            email=user.email or "",
            access_token=access_token,
            refresh_token=refresh_token,
        )


def get_auth_provider() -> AuthProvider:
    settings = get_settings()
    if settings.auth_mode == "local":
        return LocalAuthProvider()
    return SupabaseAuthProvider()
