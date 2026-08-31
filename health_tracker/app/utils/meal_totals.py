from app.models import MealEntry

MACRO_KEYS = ("calories", "protein_g", "carbs_g", "fat_g")


def meal_totals(meals: list[MealEntry]) -> dict[str, float]:
    return {
        "calories": round(sum(meal.calories or 0 for meal in meals), 1),
        "protein_g": round(sum(meal.protein_g or 0 for meal in meals), 1),
        "carbs_g": round(sum(meal.carbs_g or 0 for meal in meals), 1),
        "fat_g": round(sum(meal.fat_g or 0 for meal in meals), 1),
    }


def meal_totals_by_date(meals: list[MealEntry]) -> dict[str, dict[str, float]]:
    totals: dict[str, dict[str, float]] = {}
    for meal in meals:
        key = meal.entry_date.isoformat()
        day_total = totals.setdefault(key, {macro: 0.0 for macro in MACRO_KEYS})
        day_total["calories"] += meal.calories or 0
        day_total["protein_g"] += meal.protein_g or 0
        day_total["carbs_g"] += meal.carbs_g or 0
        day_total["fat_g"] += meal.fat_g or 0
    return {
        key: {macro: round(value, 1) for macro, value in day_total.items()}
        for key, day_total in totals.items()
    }
