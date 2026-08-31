from datetime import date

from fastapi import APIRouter, Depends, Request
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import BodyMetric, MealEntry, WorkoutEntry
from app.services.insight_service import build_daily_advice, summarize_today


router = APIRouter()
templates = Jinja2Templates(directory="app/templates")
from app.constants import MEAL_TYPE_LABELS
def dashboard(request: Request, db: Session = Depends(get_db)):
    today = date.today()
    summary = summarize_today(db, today)
    latest_body = db.query(BodyMetric).order_by(BodyMetric.entry_date.desc()).first()
    recent_meals = (
        db.query(MealEntry)
        .order_by(MealEntry.entry_date.desc(), MealEntry.created_at.desc())
        .limit(5)
        .all()
    )
    recent_workouts = (
        db.query(WorkoutEntry)
        .order_by(WorkoutEntry.entry_date.desc(), WorkoutEntry.created_at.desc())
        .limit(5)
        .all()
    )

    return templates.TemplateResponse(
        name="dashboard.html",
        request=request,
        context={
            "request": request,
            "today": today,
            "summary": summary,
            "latest_body": latest_body,
            "daily_advice": build_daily_advice(db, today),
            "recent_meals": recent_meals,
            "recent_workouts": recent_workouts,
            "meal_type_labels": MEAL_TYPE_LABELS,
            "active_page": "dashboard",
        },
    )
