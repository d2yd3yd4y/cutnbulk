import calendar
from datetime import date

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import DailyEntry


router = APIRouter(tags=["calendar"])
templates = Jinja2Templates(directory="app/templates")

WEEKDAYS = ["一", "二", "三", "四", "五", "六", "日"]


@router.get("/today")
def today_redirect():
    return RedirectResponse(url=f"/day/{date.today().isoformat()}", status_code=303)


@router.get("/")
def calendar_page(
    request: Request,
    year: int | None = Query(None),
    month: int | None = Query(None),
    db: Session = Depends(get_db),
):
    today = date.today()
    current_year = year or today.year
    current_month = month or today.month
    if current_month < 1 or current_month > 12:
        current_year, current_month = today.year, today.month

    first_day = date(current_year, current_month, 1)
    prev_year, prev_month = _shift_month(current_year, current_month, -1)
    next_year, next_month = _shift_month(current_year, current_month, 1)

    month_calendar = calendar.Calendar(firstweekday=0).monthdatescalendar(
        current_year,
        current_month,
    )
    visible_start = month_calendar[0][0]
    visible_end = month_calendar[-1][-1]
    entries = (
        db.query(DailyEntry)
        .filter(DailyEntry.entry_date >= visible_start, DailyEntry.entry_date <= visible_end)
        .all()
    )
    entries_by_date = {entry.entry_date.isoformat(): entry for entry in entries}
    current_month_entries = [
        entry for entry in entries if entry.entry_date.year == current_year and entry.entry_date.month == current_month
    ]
    weights = [entry.weight_kg for entry in current_month_entries if entry.weight_kg is not None]
    calories = [entry.calories for entry in current_month_entries if entry.calories is not None]
    training_days = len(
        [
            entry
            for entry in current_month_entries
            if entry.training_parts and entry.training_parts != "休息"
        ]
    )
    month_summary = {
        "recorded_days": len(current_month_entries),
        "average_weight": _avg(weights),
        "average_calories": _avg(calories),
        "training_days": training_days,
    }

    return templates.TemplateResponse(
        name="calendar.html",
        request=request,
        context={
            "request": request,
            "today": today,
            "first_day": first_day,
            "weeks": month_calendar,
            "weekdays": WEEKDAYS,
            "entries_by_date": entries_by_date,
            "prev_year": prev_year,
            "prev_month": prev_month,
            "next_year": next_year,
            "next_month": next_month,
            "month_summary": month_summary,
            "active_page": "calendar",
        },
    )


def _shift_month(year: int, month: int, delta: int) -> tuple[int, int]:
    shifted_month = month + delta
    if shifted_month < 1:
        return year - 1, 12
    if shifted_month > 12:
        return year + 1, 1
    return year, shifted_month


def _avg(values: list[float]) -> float | None:
    if not values:
        return None
    return round(sum(values) / len(values), 1)
