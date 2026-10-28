"""Legacy /meals page kept for compatibility; scoped to current user."""

from datetime import date

from fastapi import APIRouter, Depends, File, Form, Request, UploadFile
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import CurrentUser
from app.models import MealEntry
from app.security.csrf import validate_csrf
from app.services.nutrition_estimator import estimate_meal_nutrition
from app.services.storage import StorageError, storage_service
from app.templating import render


router = APIRouter(prefix="/meals", tags=["meals"])
MEAL_TYPE_LABELS = {
    "breakfast": "早餐",
    "lunch": "午餐",
    "dinner": "晚餐",
    "snack": "加餐",
}


@router.get("")
@router.get("/")
def meals_page(request: Request, user: CurrentUser, db: Session = Depends(get_db)):
    today = date.today()
    meals = (
        db.query(MealEntry)
        .filter(MealEntry.user_id == user.id)
        .order_by(MealEntry.entry_date.desc(), MealEntry.created_at.desc())
        .limit(80)
        .all()
    )
    today_meals = (
        db.query(MealEntry)
        .filter(MealEntry.user_id == user.id, MealEntry.entry_date == today)
        .all()
    )
    totals = {
        "calories": round(sum(meal.calories for meal in today_meals), 1),
        "protein_g": round(sum(meal.protein_g for meal in today_meals), 1),
        "carbs_g": round(sum(meal.carbs_g for meal in today_meals), 1),
        "fat_g": round(sum(meal.fat_g for meal in today_meals), 1),
    }

    return render(
        request,
        "meals.html",
        {
            "today": today,
            "meals": meals,
            "totals": totals,
            "meal_type_labels": MEAL_TYPE_LABELS,
            "templates": [],
            "active_page": "meals",
        },
        user=user,
    )


@router.post("")
@router.post("/")
async def create_meal(
    request: Request,
    user: CurrentUser,
    entry_date: date = Form(...),
    meal_type: str = Form(...),
    description: str = Form(...),
    calories: str = Form(""),
    protein_g: str = Form(""),
    carbs_g: str = Form(""),
    fat_g: str = Form(""),
    notes: str | None = Form(None),
    csrf_token: str = Form(""),
    image: UploadFile | None = File(None),
    db: Session = Depends(get_db),
):
    validate_csrf(request, csrf_token)
    image_key = None
    if image and image.filename:
        try:
            image_key = storage_service.save_meal_image(user.id, await image.read(), image.filename)
        except StorageError:
            return RedirectResponse(url="/meals", status_code=303)

    manual = any(value.strip() for value in (calories, protein_g, carbs_g, fat_g))
    if manual:
        estimate_calories = _parse_float(calories, 0)
        estimate_protein = _parse_float(protein_g, 0)
        estimate_carbs = _parse_float(carbs_g, 0)
        estimate_fat = _parse_float(fat_g, 0)
        source = "manual"
        reasoning = "已使用手动填写的营养数字。"
    else:
        estimate = estimate_meal_nutrition(db, description, None, user_id=user.id)
        estimate_calories = estimate.calories
        estimate_protein = estimate.protein_g
        estimate_carbs = estimate.carbs_g
        estimate_fat = estimate.fat_g
        source = estimate.source
        reasoning = estimate.reasoning

    meal = MealEntry(
        user_id=user.id,
        entry_date=entry_date,
        meal_type=meal_type,
        description=description.strip(),
        image_path=image_key,
        calories=estimate_calories,
        protein_g=estimate_protein,
        carbs_g=estimate_carbs,
        fat_g=estimate_fat,
        estimate_source=source,
        estimate_reasoning=reasoning,
        notes=notes,
    )
    try:
        db.add(meal)
        db.commit()
    except Exception:
        storage_service.delete_object(image_key)
        raise
    return RedirectResponse(url="/meals", status_code=303)


def _parse_float(value: str, default: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default
