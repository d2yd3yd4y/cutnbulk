from datetime import date, timedelta

from sqlalchemy.orm import Session

from app.models import BodyMetric, MealEntry, WorkoutEntry


def build_weekly_review(db: Session, end_date: date | None = None) -> dict:
    end = end_date or date.today()
    start = end - timedelta(days=6)

    meals = (
        db.query(MealEntry)
        .filter(MealEntry.entry_date >= start, MealEntry.entry_date <= end)
        .all()
    )
    workouts = (
        db.query(WorkoutEntry)
        .filter(WorkoutEntry.entry_date >= start, WorkoutEntry.entry_date <= end)
        .all()
    )
    body_metrics = (
        db.query(BodyMetric)
        .filter(BodyMetric.entry_date >= start, BodyMetric.entry_date <= end)
        .order_by(BodyMetric.entry_date.asc())
        .all()
    )

    recorded_days = len(
        {
            *[meal.entry_date for meal in meals],
            *[workout.entry_date for workout in workouts],
            *[metric.entry_date for metric in body_metrics],
        }
    )
    day_count = 7

    total_calories = sum(meal.calories for meal in meals)
    total_protein = sum(meal.protein_g for meal in meals)
    total_carbs = sum(meal.carbs_g for meal in meals)
    total_fat = sum(meal.fat_g for meal in meals)
    total_sets = sum(workout.sets for workout in workouts)
    total_volume = sum(workout.volume for workout in workouts)

    sleep_values = [metric.sleep_hours for metric in body_metrics if metric.sleep_hours is not None]
    fatigue_values = [
        metric.fatigue_level for metric in body_metrics if metric.fatigue_level is not None
    ]
    weight_values = [metric.weight_kg for metric in body_metrics if metric.weight_kg is not None]
    waist_values = [metric.waist_cm for metric in body_metrics if metric.waist_cm is not None]

    review = {
        "start_date": start,
        "end_date": end,
        "recorded_days": recorded_days,
        "average_calories": _avg(total_calories, day_count),
        "average_protein": _avg(total_protein, day_count),
        "average_carbs": _avg(total_carbs, day_count),
        "average_fat": _avg(total_fat, day_count),
        "total_sets": total_sets,
        "total_volume": round(total_volume, 1),
        "weight_trend": _trend(weight_values, "kg"),
        "waist_trend": _trend(waist_values, "cm"),
        "average_sleep": _avg(sum(sleep_values), len(sleep_values)) if sleep_values else None,
        "average_fatigue": _avg(sum(fatigue_values), len(fatigue_values)) if fatigue_values else None,
        "summary": "",
        "body_metrics": body_metrics,
    }
    review["summary"] = _build_summary(review, weight_values, waist_values)
    return review


def _avg(total: float, count: int) -> float:
    if count <= 0:
        return 0
    return round(total / count, 1)


def _trend(values: list[float], unit: str) -> str:
    if len(values) < 2:
        return "数据不足"
    diff = round(values[-1] - values[0], 1)
    if diff > 0:
        return f"上升 {diff}{unit}"
    if diff < 0:
        return f"下降 {abs(diff)}{unit}"
    return "基本持平"


def _build_summary(review: dict, weight_values: list[float], waist_values: list[float]) -> str:
    messages: list[str] = []
    if review["recorded_days"] < 3:
        messages.append("记录满 3 天后复盘会更准确。")

    sleep_low = review["average_sleep"] is not None and review["average_sleep"] < 6.8
    fatigue_high = review["average_fatigue"] is not None and review["average_fatigue"] >= 7
    if review["total_volume"] > 12000 and (sleep_low or fatigue_high):
        messages.append("最近训练量不低，同时睡眠或疲劳指标不太理想，建议先关注恢复质量。")

    if len(weight_values) >= 2 and len(waist_values) >= 2:
        weight_diff = weight_values[-1] - weight_values[0]
        waist_diff = waist_values[-1] - waist_values[0]
        if abs(weight_diff) < 0.3 and waist_diff < -0.5:
            messages.append("体重暂时没变但腰围下降，方向可能是对的，先不要急着继续降低热量。")

    if review["average_protein"] < 90 and review["recorded_days"] >= 3:
        messages.append("最近 7 天蛋白质偏低，优先把每餐蛋白质补足，比继续压热量更重要。")

    if review["average_carbs"] < 150 and review["total_volume"] > 10000:
        messages.append("碳水偏低且训练量较高，训练日前后可以增加一份主食。")

    if not messages:
        messages.append("这一周整体比较稳定，继续保持记录节奏，再根据体重、腰围和训练表现微调。")

    return " ".join(messages)
