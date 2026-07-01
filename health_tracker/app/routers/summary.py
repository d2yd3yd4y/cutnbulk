from datetime import date, timedelta

from fastapi import APIRouter, Depends, Request
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import DailyEntry


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
    weights = [entry.weight_kg for entry in entries if entry.weight_kg is not None]
    calories = [entry.calories for entry in entries if entry.calories is not None]
    protein = [entry.protein_g for entry in entries if entry.protein_g is not None]
    training_days = len(
        [entry for entry in entries if entry.training_parts and entry.training_parts != "休息"]
    )
    summary = {
        "recorded_days": len(entries),
        "average_weight": _avg(weights),
        "average_calories": _avg(calories),
        "average_protein": _avg(protein),
        "training_days": training_days,
        "advice": _build_advice(len(entries), _avg(protein), _avg(calories), training_days),
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
