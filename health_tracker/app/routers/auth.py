from __future__ import annotations

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.auth.provider import AuthError, get_auth_provider
from app.auth.session_service import session_service
from app.config import get_settings
from app.database import get_db
from app.deps import OptionalUser
from app.security.csrf import ensure_csrf_cookie, validate_csrf
from app.security.rate_limit import rate_limiter
from app.utils.urls import safe_next_path


router = APIRouter(tags=["auth"])
templates = Jinja2Templates(directory="app/templates")


def _client_key(request: Request, action: str) -> str:
    host = request.client.host if request.client else "unknown"
    return f"{action}:{host}"


def _render_auth(
    request: Request,
    template: str,
    *,
    error: str | None = None,
    message: str | None = None,
    email: str = "",
    next_path: str = "/",
    status_code: int = 200,
):
    response = templates.TemplateResponse(
        name=template,
        request=request,
        context={
            "request": request,
            "error": error,
            "message": message,
            "email": email,
            "next_path": next_path,
            "csrf_token": ensure_csrf_cookie(request),
            "active_page": None,
            "hide_nav": True,
            "current_user": None,
        },
        status_code=status_code,
    )
    ensure_csrf_cookie(request, response)
    return response


@router.get("/register", response_class=HTMLResponse)
def register_page(request: Request, user: OptionalUser, next: str = "/"):
    if user:
        return RedirectResponse(url=safe_next_path(next), status_code=303)
    return _render_auth(request, "auth/register.html", next_path=safe_next_path(next))


@router.post("/register")
def register(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    confirm_password: str = Form(...),
    csrf_token: str = Form(""),
    next: str = Form("/"),
    db: Session = Depends(get_db),
):
    validate_csrf(request, csrf_token)
    next_path = safe_next_path(next)
    if not rate_limiter.hit(_client_key(request, "register"), limit=10, window_seconds=600):
        return _render_auth(
            request,
            "auth/register.html",
            error="尝试次数过多，请稍后再试。",
            email=email,
            next_path=next_path,
            status_code=429,
        )
    if len(password) < 8:
        return _render_auth(
            request,
            "auth/register.html",
            error="密码至少 8 位。",
            email=email,
            next_path=next_path,
            status_code=400,
        )
    if password != confirm_password:
        return _render_auth(
            request,
            "auth/register.html",
            error="两次输入的密码不一致。",
            email=email,
            next_path=next_path,
            status_code=400,
        )
    try:
        result = get_auth_provider().register(db, email, password)
    except AuthError as exc:
        return _render_auth(
            request,
            "auth/register.html",
            error=exc.message,
            email=email,
            next_path=next_path,
            status_code=400,
        )

    if result.needs_email_verification or not result.access_token:
        return _render_auth(
            request,
            "auth/login.html",
            message=result.message or "注册成功，请查收验证邮件后再登录。",
            email=email,
            next_path=next_path,
        )

    redirect = RedirectResponse(url=next_path, status_code=303)
    session_service.create_session(db, result, redirect)
    ensure_csrf_cookie(request, redirect)
    return redirect


@router.get("/login", response_class=HTMLResponse)
def login_page(request: Request, user: OptionalUser, next: str = "/"):
    if user:
        return RedirectResponse(url=safe_next_path(next), status_code=303)
    return _render_auth(request, "auth/login.html", next_path=safe_next_path(next))


@router.post("/login")
def login(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    csrf_token: str = Form(""),
    next: str = Form("/"),
    db: Session = Depends(get_db),
):
    validate_csrf(request, csrf_token)
    next_path = safe_next_path(next)
    if not rate_limiter.hit(_client_key(request, "login"), limit=20, window_seconds=600):
        return _render_auth(
            request,
            "auth/login.html",
            error="尝试次数过多，请稍后再试。",
            email=email,
            next_path=next_path,
            status_code=429,
        )
    try:
        result = get_auth_provider().login(db, email, password)
    except AuthError as exc:
        return _render_auth(
            request,
            "auth/login.html",
            error=exc.message,
            email=email,
            next_path=next_path,
            status_code=400,
        )

    redirect = RedirectResponse(url=next_path, status_code=303)
    session_service.create_session(db, result, redirect)
    ensure_csrf_cookie(request, redirect)
    return redirect


@router.post("/logout")
def logout(
    request: Request,
    csrf_token: str = Form(""),
    db: Session = Depends(get_db),
):
    validate_csrf(request, csrf_token)
    settings = get_settings()
    session_id = request.cookies.get(settings.session_cookie_name)
    redirect = RedirectResponse(url="/login", status_code=303)
    session_service.revoke_session(db, session_id, redirect)
    ensure_csrf_cookie(request, redirect)
    return redirect


@router.get("/forgot-password", response_class=HTMLResponse)
def forgot_password_page(request: Request):
    return _render_auth(request, "auth/forgot_password.html")


@router.post("/forgot-password")
def forgot_password(
    request: Request,
    email: str = Form(...),
    csrf_token: str = Form(""),
):
    validate_csrf(request, csrf_token)
    if not rate_limiter.hit(_client_key(request, "forgot"), limit=5, window_seconds=600):
        return _render_auth(
            request,
            "auth/forgot_password.html",
            error="尝试次数过多，请稍后再试。",
            email=email,
            status_code=429,
        )
    get_auth_provider().request_password_reset(email)
    return _render_auth(
        request,
        "auth/forgot_password.html",
        message="如果该邮箱已注册，重置邮件将很快送达。请查收邮箱。",
        email=email,
    )


@router.get("/auth/callback")
def auth_callback(request: Request, next: str = "/"):
    """Email verification / magic-link landing. Tokens may arrive in URL hash (client)."""
    return _render_auth(
        request,
        "auth/callback.html",
        message="正在完成验证，请稍候…",
        next_path=safe_next_path(next),
    )


@router.get("/auth/reset-password", response_class=HTMLResponse)
def reset_password_page(request: Request):
    return _render_auth(request, "auth/reset_password.html")


@router.post("/auth/reset-password")
def reset_password(
    request: Request,
    password: str = Form(...),
    confirm_password: str = Form(...),
    access_token: str = Form(""),
    refresh_token: str = Form(""),
    csrf_token: str = Form(""),
    db: Session = Depends(get_db),
):
    validate_csrf(request, csrf_token)
    if len(password) < 8:
        return _render_auth(
            request,
            "auth/reset_password.html",
            error="密码至少 8 位。",
            status_code=400,
        )
    if password != confirm_password:
        return _render_auth(
            request,
            "auth/reset_password.html",
            error="两次输入的密码不一致。",
            status_code=400,
        )
    if not access_token:
        return _render_auth(
            request,
            "auth/reset_password.html",
            error="重置链接无效或已过期，请重新申请。",
            status_code=400,
        )
    provider = get_auth_provider()
    try:
        auth = provider.exchange_recovery_session(access_token, refresh_token or access_token)
        provider.update_password(access_token, password)
    except AuthError as exc:
        return _render_auth(
            request,
            "auth/reset_password.html",
            error=exc.message,
            status_code=400,
        )

    redirect = RedirectResponse(url="/", status_code=303)
    session_service.create_session(db, auth, redirect)
    ensure_csrf_cookie(request, redirect)
    return redirect


@router.post("/auth/session-from-tokens")
def session_from_tokens(
    request: Request,
    access_token: str = Form(...),
    refresh_token: str = Form(""),
    csrf_token: str = Form(""),
    next: str = Form("/"),
    db: Session = Depends(get_db),
):
    """Convert Supabase browser hash tokens into a server session cookie."""
    validate_csrf(request, csrf_token)
    next_path = safe_next_path(next)
    try:
        auth = get_auth_provider().exchange_recovery_session(access_token, refresh_token or access_token)
        # Ensure profile exists
        from app.models import UserProfile

        profile = db.query(UserProfile).filter(UserProfile.id == auth.user_id).first()
        if profile is None:
            profile = UserProfile(id=auth.user_id, email=auth.email or f"{auth.user_id}@unknown")
            db.add(profile)
            db.commit()
    except AuthError as exc:
        return _render_auth(
            request,
            "auth/login.html",
            error=exc.message,
            next_path=next_path,
            status_code=400,
        )
    redirect = RedirectResponse(url=next_path, status_code=303)
    session_service.create_session(db, auth, redirect)
    ensure_csrf_cookie(request, redirect)
    return redirect
