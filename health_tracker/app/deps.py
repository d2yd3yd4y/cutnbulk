from __future__ import annotations

from typing import Annotated

from fastapi import Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.auth.session_service import session_service
from app.config import get_settings
from app.database import get_db
from app.exceptions import AuthRedirect
from app.models import UserProfile
from app.security.csrf import ensure_csrf_cookie
from app.utils.urls import safe_next_path


def _wants_json(request: Request) -> bool:
    accept = request.headers.get("accept", "")
    return "application/json" in accept or request.url.path.startswith("/api/")


def get_current_user(
    request: Request,
    db: Session = Depends(get_db),
) -> UserProfile:
    settings = get_settings()
    session_id = request.cookies.get(settings.session_cookie_name)
    user = session_service.get_user_for_request(db, session_id)
    if user is None:
        if _wants_json(request):
            raise HTTPException(status_code=401, detail="未登录")
        next_path = request.url.path
        if request.url.query:
            next_path = f"{next_path}?{request.url.query}"
        raise AuthRedirect(f"/login?next={safe_next_path(next_path)}")
    request.state.user = user
    ensure_csrf_cookie(request)
    return user


def get_optional_user(
    request: Request,
    db: Session = Depends(get_db),
) -> UserProfile | None:
    settings = get_settings()
    session_id = request.cookies.get(settings.session_cookie_name)
    user = session_service.get_user_for_request(db, session_id)
    if user:
        request.state.user = user
        ensure_csrf_cookie(request)
    return user


CurrentUser = Annotated[UserProfile, Depends(get_current_user)]
OptionalUser = Annotated[UserProfile | None, Depends(get_optional_user)]
