from datetime import date
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, File, Form, Request, UploadFile
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import MealEntry
from app.services.food_ai_service import TEMPLATE_ESTIMATES, estimate_food_nutrition


router = APIRouter(prefix="/meals", tags=["meals"])
templates = Jinja2Templates(directory="app/templates")
UPLOAD_DIR = Path("app/uploads")
MEAL_TYPE_LABELS = {
    "breakfast": "早餐",
    "lunch": "午餐",
    "dinner": "晚餐",
    "snack": "加餐",
}


@router.get("")
@router.get("/")
def meals_page(request: Request, db: Session = Depends(get_db)):
    today = date.today()
    meals = (
        db.query(MealEntry)
        .order_by(MealEntry.entry_date.desc(), MealEntry.created_at.desc())
        .limit(80)
        .all()
    )
    today_meals = db.query(MealEntry).filter(MealEntry.entry_date == today).all()
    totals = {
        "calories": round(sum(meal.calories for meal in today_meals), 1),
        "protein_g": round(sum(meal.protein_g for meal in today_meals), 1),
        "carbs_g": round(sum(meal.carbs_g for meal in today_meals), 1),
        "fat_g": round(sum(meal.fat_g for meal in today_meals), 1),
    }

    return templates.TemplateResponse(
        name="meals.html",
        request=request,
        context={
            "request": request,
            "today": today,
            "meals": meals,
            "totals": totals,
            "meal_type_labels": MEAL_TYPE_LABELS,
            "templates": list(TEMPLATE_ESTIMATES.keys()),
            "active_page": "meals",
        },
    )


@router.post("")
@router.post("/")
async def create_meal(
    entry_date: date = Form(...),
    meal_type: str = Form(...),
    description: str = Form(...),
    calories: str = Form(""),
    protein_g: str = Form(""),
    carbs_g: str = Form(""),
    fat_g: str = Form(""),
    notes: str | None = Form(None),
    image: UploadFile | None = File(None),
    db: Session = Depends(get_db),
):
    image_path = await _save_upload(image)
    estimate = estimate_food_nutrition(description, image_path)

    meal = MealEntry(
        entry_date=entry_date,
        meal_type=meal_type,
        description=description.strip(),
        image_path=image_path,
        calories=_parse_float(calories, estimate.calories),
        protein_g=_parse_float(protein_g, estimate.protein_g),
        carbs_g=_parse_float(carbs_g, estimate.carbs_g),
        fat_g=_parse_float(fat_g, estimate.fat_g),
        notes=notes,
    )
    db.add(meal)
    db.commit()
    return RedirectResponse(url="/meals", status_code=303)


async def _save_upload(image: UploadFile | None) -> str | None:
    if not image or not image.filename:
        return None

    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    suffix = Path(image.filename).suffix.lower() or ".jpg"
    filename = f"{uuid4().hex}{suffix}"
    destination = UPLOAD_DIR / filename
    content = await image.read()
    destination.write_bytes(content)
    return f"/uploads/{filename}"


def _parse_float(value: str, default: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default
