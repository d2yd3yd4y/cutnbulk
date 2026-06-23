from fastapi import APIRouter, Depends, Request
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.database import get_db
from app.services.weekly_review_service import build_weekly_review


router = APIRouter(prefix="/weekly", tags=["weekly"])
templates = Jinja2Templates(directory="app/templates")


@router.get("")
@router.get("/")
def weekly_page(request: Request, db: Session = Depends(get_db)):
    return templates.TemplateResponse(
        name="weekly.html",
        request=request,
        context={
            "request": request,
            "review": build_weekly_review(db),
            "active_page": "weekly",
        },
    )
