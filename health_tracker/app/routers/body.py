from datetime import date

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import BodyMetric


router = APIRouter(prefix="/body", tags=["body"])
templates = Jinja2Templates(directory="app/templates")


@router.get("")
@router.get("/")
def body_page(request: Request, db: Session = Depends(get_db)):
    today = date.today()
    metrics = (
        db.query(BodyMetric)
        .order_by(BodyMetric.entry_date.desc(), BodyMetric.created_at.desc())
        .limit(100)
        .all()
    )

    return templates.TemplateResponse(
        name="body.html",
        request=request,
        context={
            "request": request,
            "today": today,
            "metrics": metrics,
            "active_page": "body",
        },
    )


@router.post("")
@router.post("/")
def upsert_body_metric(
    entry_date: date = Form(...),
    weight_kg: str = Form(""),
    waist_cm: str = Form(""),
    sleep_hours: str = Form(""),
    fatigue_level: str = Form(""),
    notes: str | None = Form(None),
    db: Session = Depends(get_db),
):
    metric = db.query(BodyMetric).filter(BodyMetric.entry_date == entry_date).first()
    if metric is None:
        metric = BodyMetric(entry_date=entry_date)
        db.add(metric)

    metric.weight_kg = _parse_float(weight_kg)
    metric.waist_cm = _parse_float(waist_cm)
    metric.sleep_hours = _parse_float(sleep_hours)
    metric.fatigue_level = _parse_int(fatigue_level)
    metric.notes = notes
    db.commit()
    return RedirectResponse(url="/body", status_code=303)


def _parse_float(value: str) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _parse_int(value: str) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None
