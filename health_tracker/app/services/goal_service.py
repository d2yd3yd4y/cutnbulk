from dataclasses import dataclass
from datetime import date

from sqlalchemy.orm import Session

from app.models import GoalSetting, MealEntry
from app.utils.meal_totals import meal_totals


KCAL_PER_KG = 7700
ACTIVITY_FACTORS = {
    "sedentary": 28,
    "light": 31,
    "moderate": 34,
    "active": 38,
}
MODE_LABELS = {
    "cut": "减脂",
    "maintain": "维持",
    "bulk": "增肌",
}
ACTIVITY_LABELS = {
    "sedentary": "久坐",
    "light": "轻度活动",
    "moderate": "中等活动",
    "active": "高活动",
}


@dataclass(frozen=True)
class GoalCalculation:
    mode: str
    current_weight_kg: float
    target_weight_kg: float
    target_days: int
    activity_level: str
    maintenance_calories: float
    recommended_calories: float
    weight_delta: float
    total_energy_delta: float
    daily_energy_delta: float
    weekly_weight_change: float
    note: str


def validate_goal(
    mode: str,
    current_weight_kg: float,
    target_weight_kg: float,
    target_days: int,
) -> str | None:
    if mode not in MODE_LABELS:
        return "请选择有效的目标阶段。"
    if current_weight_kg <= 0 or target_weight_kg <= 0:
        return "体重需要大于 0。"
    if target_days <= 0:
        return "目标天数需要大于 0。"
    if mode == "cut" and target_weight_kg >= current_weight_kg:
        return "减脂目标体重应低于当前体重。"
    if mode == "bulk" and target_weight_kg <= current_weight_kg:
        return "增肌目标体重应高于当前体重。"
    return None


def calculate_goal(
    mode: str,
    current_weight_kg: float,
    target_weight_kg: float,
    target_days: int,
    activity_level: str = "moderate",
    maintenance_calories: float | None = None,
) -> GoalCalculation:
    activity = activity_level if activity_level in ACTIVITY_FACTORS else "moderate"
    estimated_maintenance = current_weight_kg * ACTIVITY_FACTORS[activity]
    final_maintenance = maintenance_calories or estimated_maintenance

    weight_delta = target_weight_kg - current_weight_kg
    if mode == "maintain":
        weight_delta = 0

    total_energy_delta = weight_delta * KCAL_PER_KG
    daily_energy_delta = total_energy_delta / target_days if target_days else 0
    recommended_calories = final_maintenance + daily_energy_delta
    if mode == "maintain":
        recommended_calories = final_maintenance
        daily_energy_delta = 0

    weekly_weight_change = weight_delta / target_days * 7 if target_days else 0
    note = build_goal_note(
        mode=mode,
        current_weight_kg=current_weight_kg,
        target_days=target_days,
        daily_energy_delta=daily_energy_delta,
        weekly_weight_change=weekly_weight_change,
    )

    return GoalCalculation(
        mode=mode,
        current_weight_kg=round(current_weight_kg, 1),
        target_weight_kg=round(target_weight_kg, 1),
        target_days=target_days,
        activity_level=activity,
        maintenance_calories=round(final_maintenance),
        recommended_calories=round(recommended_calories),
        weight_delta=round(weight_delta, 1),
        total_energy_delta=round(total_energy_delta),
        daily_energy_delta=round(daily_energy_delta),
        weekly_weight_change=round(weekly_weight_change, 2),
        note=note,
    )


def build_goal_note(
    mode: str,
    current_weight_kg: float,
    target_days: int,
    daily_energy_delta: float,
    weekly_weight_change: float,
) -> str:
    notes: list[str] = []
    if target_days < 14:
        notes.append("目标周期太短，建议至少设置 2-4 周以上。")
    if abs(weekly_weight_change) > current_weight_kg * 0.01:
        notes.append("目标速度偏快，建议考虑拉长周期。")

    if mode == "cut":
        deficit = abs(daily_energy_delta)
        if deficit > 750:
            notes.append("这个减脂速度偏激进，可能影响训练表现和恢复。")
        elif 300 <= deficit <= 500:
            notes.append("这是相对稳妥的减脂区间。")
        else:
            notes.append("保持稳定记录，根据体重趋势再微调热量。")
    elif mode == "bulk":
        surplus = daily_energy_delta
        if surplus > 500:
            notes.append("这个增肌盈余偏高，可能更容易增加脂肪。")
        elif 150 <= surplus <= 300:
            notes.append("这是比较稳妥的增肌区间。")
        else:
            notes.append("增肌期优先保证训练表现和蛋白质摄入。")
    else:
        notes.append("维持阶段适合观察训练表现、体重和饮食稳定性。")

    return " ".join(notes)


def get_active_goal(db: Session) -> GoalSetting | None:
    return (
        db.query(GoalSetting)
        .filter(GoalSetting.is_active.is_(True))
        .order_by(GoalSetting.updated_at.desc(), GoalSetting.id.desc())
        .first()
    )


def get_goal_progress_for_day(db: Session, target_date: date) -> dict:
    goal = get_active_goal(db)
    meals = db.query(MealEntry).filter(MealEntry.entry_date == target_date).all()
    consumed = meal_totals(meals)["calories"]
    recommended = goal.recommended_calories if goal else None
    remaining = round(recommended - consumed, 1) if recommended is not None else None
    return {
        "goal": goal,
        "consumed_calories": consumed,
        "recommended_calories": recommended,
        "remaining_calories": remaining,
        "is_over": remaining is not None and remaining < 0,
    }


def mode_label(mode: str) -> str:
    return MODE_LABELS.get(mode, mode)
