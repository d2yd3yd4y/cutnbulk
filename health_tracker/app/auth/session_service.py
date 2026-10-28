from __future__ import annotations

from datetime import datetime, timedelta
from uuid import uuid4

from fastapi import Response
from sqlalchemy.orm import Session

from app.auth.provider import AuthResult, get_auth_provider
from app.config import get_settings
from app.models import AuthSession, UserProfile


class SessionService:
    def create_session(self, db: Session, auth: AuthResult, response: Response) -> AuthSession:
        settings = get_settings()
        session = AuthSession(
            id=uuid4().hex,
            user_id=auth.user_id,
            access_token=auth.access_token,
            refresh_token=auth.refresh_token,
            expires_at=datetime.utcnow() + timedelta(days=settings.session_ttl_days),
        )
        db.add(session)
        db.commit()
        self._set_cookie(response, session.id)
        return session

    def revoke_session(self, db: Session, session_id: str | None, response: Response) -> None:
        if session_id:
            session = db.query(AuthSession).filter(AuthSession.id == session_id).first()
            if session and session.revoked_at is None:
                session.revoked_at = datetime.utcnow()
                db.commit()
        self.clear_cookie(response)

    def get_user_for_request(self, db: Session, session_id: str | None) -> UserProfile | None:
        if not session_id:
            return None
        session = (
            db.query(AuthSession)
            .filter(AuthSession.id == session_id, AuthSession.revoked_at.is_(None))
            .first()
        )
        if session is None:
            return None
        if session.expires_at and session.expires_at < datetime.utcnow():
            session.revoked_at = datetime.utcnow()
            db.commit()
            return None

        # Best-effort refresh for Supabase tokens.
        settings = get_settings()
        if (
            settings.auth_mode == "supabase"
            and session.refresh_token
            and session.refresh_token != "local"
        ):
            try:
                refreshed = get_auth_provider().refresh(session.refresh_token)
                session.access_token = refreshed.access_token
                session.refresh_token = refreshed.refresh_token
                session.last_seen_at = datetime.utcnow()
                db.commit()
            except Exception:
                # Keep existing session until cookie TTL unless refresh hard-fails repeatedly.
                pass
        else:
            session.last_seen_at = datetime.utcnow()
            db.commit()

        return db.query(UserProfile).filter(UserProfile.id == session.user_id).first()

    def _set_cookie(self, response: Response, session_id: str) -> None:
        settings = get_settings()
        response.set_cookie(
            key=settings.session_cookie_name,
            value=session_id,
            httponly=True,
            secure=settings.cookie_secure,
            samesite="lax",
            max_age=60 * 60 * 24 * settings.session_ttl_days,
            path="/",
        )

    def clear_cookie(self, response: Response) -> None:
        settings = get_settings()
        response.delete_cookie(key=settings.session_cookie_name, path="/")


session_service = SessionService()
