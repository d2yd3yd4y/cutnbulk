from __future__ import annotations

from datetime import date

from fastapi import Request
from fastapi.templating import Jinja2Templates

from app.models import UserProfile
from app.security.csrf import ensure_csrf_cookie


templates = Jinja2Templates(directory="app/templates")


def render(
    request: Request,
    name: str,
    context: dict,
    *,
    user: UserProfile | None = None,
    status_code: int = 200,
):
    payload = {
        "request": request,
        "today": context.get("today", date.today()),
        "current_user": user,
        "csrf_token": ensure_csrf_cookie(request),
        "hide_nav": context.get("hide_nav", False),
    }
    payload.update(context)
    response = templates.TemplateResponse(
        name=name,
        request=request,
        context=payload,
        status_code=status_code,
    )
    ensure_csrf_cookie(request, response)
    return response
