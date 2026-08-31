from datetime import date, timedelta

from fastapi import APIRouter, Depends, Request
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import DailyEntry, MealEntry
from app.utils.meal_totals import meal_totals_by_date as build_meal_totals_by_date
from app.utils.stats import avg_values


router = APIRouter(prefix="/summary", tags=["summary"])
templates = Jinja2Templates(directory="app/templates")


@router.get("")
@router.get("/")
def summary_page(request: Request, db: Session = Depends(get_db)):
    today = date.today()
    start = today - timedelta(days=6)
    entries = (
        db.query(DailyEntry)
        .filter(DailyEntry.entry_date >= start, DailyEntry.entry_date <= today)
        .order_by(DailyEntry.entry_date.desc())
        .all()
    )
    meals = (
        db.query(MealEntry)
        .filter(MealEntry.entry_date >= start, MealEntry.entry_date <= today)
        .all()
    )
    entries_by_date = {entry.entry_date.isoformat(): entry for entry in entries}
    totals_by_date = build_meal_totals_by_date(meals)
    recent_days = sorted(
        {
            *entries_by_date.keys(),
            *totals_by_date.keys(),
        },
        reverse=True,
    )
    daily_meal_totals = list(totals_by_date.values())
    weights = [entry.weight_kg for entry in entries if entry.weight_kg is not None]
    calories = [totals["calories"] for totals in daily_meal_totals]
    protein = [totals["protein_g"] for totals in daily_meal_totals]
    carbs = [totals["carbs_g"] for totals in daily_meal_totals]
    fat = [totals["fat_g"] for totals in daily_meal_totals]
    training_days = len(
        [entry for entry in entries if entry.training_parts and entry.training_parts != "休息"]
    )
    summary = {
        "recorded_days": len(recent_days),
        "average_weight": avg_values(weights),
        "average_calories": avg_values(calories),
        "average_protein": avg_values(protein),
        "average_carbs": avg_values(carbs),
        "average_fat": avg_values(fat),
        "training_days": training_days,
        "advice": _build_advice(len(recent_days), avg_values(protein), avg_values(calories), training_days),
    }

    return templates.TemplateResponse(
        name="summary.html",
        request=request,
        context={
            "request": request,
            "today": today,
            "start": start,
            "summary": summary,
            "entries": entries,
            "entries_by_date": entries_by_date,
            "meal_totals_by_date": totals_by_date,
            "recent_days": recent_days,
            "active_page": "summary",
        },
    )


def _build_advice(
    recorded_days: int,
    average_protein: float | None,
    average_calories: float | None,
    training_days: int,
) -> str:
    if recorded_days < 3:
        return "先记录满 3 天，趋势会更有参考价值。"
    if average_protein is not None and average_protein < 90:
        return "最近蛋白质偏低，优先把每餐蛋白质补足。"
    if training_days >= 4 and average_calories is not None and average_calories < 1800:
        return "训练天数不少，热量不要压得太低，注意恢复。"
    return "这一周记录节奏不错，继续保持简单稳定。"
