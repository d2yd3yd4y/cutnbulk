from datetime import date

from sqlalchemy.orm import Session

from app.models import BodyMetric, MealEntry, WorkoutEntry
from app.utils.meal_totals import meal_totals


def build_daily_advice(db: Session, target_date: date) -> str:
    meals = db.query(MealEntry).filter(MealEntry.entry_date == target_date).all()
    workouts = db.query(WorkoutEntry).filter(WorkoutEntry.entry_date == target_date).all()
    body = (
        db.query(BodyMetric)
        .filter(BodyMetric.entry_date == target_date)
        .order_by(BodyMetric.entry_date.desc())
        .first()
    )

    totals = meal_totals(meals)
    calories = totals["calories"]
    protein = totals["protein_g"]
    carbs = totals["carbs_g"]
    total_sets = sum(workout.sets for workout in workouts)
    total_volume = sum(workout.volume for workout in workouts)

    if total_volume > 5000 and carbs < 180:
        return "今天训练量不低，但碳水偏少，晚餐可以加一份主食帮助恢复。"
    if protein and protein < 90:
        return "今天蛋白质还有提升空间，下一餐优先补足肉蛋奶豆类。"
    if body and body.sleep_hours is not None and body.sleep_hours < 6.5:
        return "昨晚睡眠偏少，今天训练和饮食保持稳定即可，不需要额外给自己压力。"
    if body and body.fatigue_level is not None and body.fatigue_level >= 8:
        return "今天疲劳感偏高，训练可以适当保留余力，把恢复放在优先级前面。"
    if calories == 0 and total_sets == 0:
        return "先记录一餐或一次训练，数据越连续，建议会越贴合你的实际情况。"
    if calories < 1600 and total_sets > 10:
        return "今天活动不少，热量可能偏低，注意别让恢复和心情被过度节食影响。"
    return "今天的记录方向不错，继续保持稳定输入，比追求完美更重要。"


def summarize_today(db: Session, target_date: date) -> dict[str, float | int]:
    meals = db.query(MealEntry).filter(MealEntry.entry_date == target_date).all()
    workouts = db.query(WorkoutEntry).filter(WorkoutEntry.entry_date == target_date).all()
    totals = meal_totals(meals)
    return {
        **totals,
        "workout_sets": sum(workout.sets for workout in workouts),
        "workout_volume": round(sum(workout.volume for workout in workouts), 1),
    }
