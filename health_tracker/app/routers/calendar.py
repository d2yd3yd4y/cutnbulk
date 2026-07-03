import calendar
from datetime import date

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import DailyEntry, MealEntry
from app.services.goal_service import MODE_LABELS, get_active_goal, get_goal_progress_for_day


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
    meals = (
        db.query(MealEntry)
        .filter(MealEntry.entry_date >= visible_start, MealEntry.entry_date <= visible_end)
        .all()
    )
    meal_totals_by_date = _meal_totals_by_date(meals)
    current_month_entries = [
        entry for entry in entries if entry.entry_date.year == current_year and entry.entry_date.month == current_month
    ]
    current_month_meal_totals = [
        totals
        for day_key, totals in meal_totals_by_date.items()
        if _date_in_month(day_key, current_year, current_month)
    ]
    recorded_dates = {
        *[entry.entry_date.isoformat() for entry in current_month_entries],
        *[
            day_key
            for day_key in meal_totals_by_date
            if _date_in_month(day_key, current_year, current_month)
        ],
    }
    weights = [entry.weight_kg for entry in current_month_entries if entry.weight_kg is not None]
    calories = [totals["calories"] for totals in current_month_meal_totals]
    training_days = len(
        [
            entry
            for entry in current_month_entries
            if entry.training_parts and entry.training_parts != "休息"
        ]
    )
    month_summary = {
        "recorded_days": len(recorded_dates),
        "average_weight": _avg(weights),
        "average_calories": _avg(calories),
        "training_days": training_days,
    }
    active_goal = get_active_goal(db)
    today_goal_progress = get_goal_progress_for_day(db, today)

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
            "meal_totals_by_date": meal_totals_by_date,
            "prev_year": prev_year,
            "prev_month": prev_month,
            "next_year": next_year,
            "next_month": next_month,
            "month_summary": month_summary,
            "active_goal": active_goal,
            "today_goal_progress": today_goal_progress,
            "mode_labels": MODE_LABELS,
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


def _meal_totals_by_date(meals: list[MealEntry]) -> dict[str, dict[str, float]]:
    totals: dict[str, dict[str, float]] = {}
    for meal in meals:
        key = meal.entry_date.isoformat()
        day_total = totals.setdefault(
            key,
            {"calories": 0, "protein_g": 0, "carbs_g": 0, "fat_g": 0},
        )
        day_total["calories"] += meal.calories or 0
        day_total["protein_g"] += meal.protein_g or 0
        day_total["carbs_g"] += meal.carbs_g or 0
        day_total["fat_g"] += meal.fat_g or 0
    return {
        key: {macro: round(value, 1) for macro, value in day_total.items()}
        for key, day_total in totals.items()
    }


def _date_in_month(day_key: str, year: int, month: int) -> bool:
    parsed = date.fromisoformat(day_key)
    return parsed.year == year and parsed.month == month
