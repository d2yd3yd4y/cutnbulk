from datetime import date, timedelta

from fastapi import APIRouter, Depends, Request
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import DailyEntry, MealEntry


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
    meal_totals_by_date = _meal_totals_by_date(meals)
    recent_days = sorted(
        {
            *entries_by_date.keys(),
            *meal_totals_by_date.keys(),
        },
        reverse=True,
    )
    daily_meal_totals = list(meal_totals_by_date.values())
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
        "average_weight": _avg(weights),
        "average_calories": _avg(calories),
        "average_protein": _avg(protein),
        "average_carbs": _avg(carbs),
        "average_fat": _avg(fat),
        "training_days": training_days,
        "advice": _build_advice(len(recent_days), _avg(protein), _avg(calories), training_days),
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
            "meal_totals_by_date": meal_totals_by_date,
            "recent_days": recent_days,
            "active_page": "summary",
        },
    )


def _avg(values: list[float]) -> float | None:
    if not values:
        return None
    return round(sum(values) / len(values), 1)


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
