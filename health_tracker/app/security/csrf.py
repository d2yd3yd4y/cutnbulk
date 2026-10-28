from __future__ import annotations

import secrets

from fastapi import HTTPException, Request, Response

from app.config import get_settings


def ensure_csrf_cookie(request: Request, response: Response | None = None) -> str:
    settings = get_settings()
    token = getattr(request.state, "csrf_token", None) or request.cookies.get(settings.csrf_cookie_name)
    if not token:
        token = secrets.token_urlsafe(32)
    request.state.csrf_token = token
    if response is not None:
        response.set_cookie(
            key=settings.csrf_cookie_name,
            value=token,
            httponly=False,
            secure=settings.cookie_secure,
            samesite="lax",
            max_age=60 * 60 * 24 * 14,
            path="/",
        )
    return token


def validate_csrf(request: Request, form_token: str | None) -> None:
    settings = get_settings()
    cookie_token = request.cookies.get(settings.csrf_cookie_name)
    if not cookie_token or not form_token or not secrets.compare_digest(cookie_token, form_token):
        raise HTTPException(status_code=403, detail="请求已过期，请刷新页面后重试。")
