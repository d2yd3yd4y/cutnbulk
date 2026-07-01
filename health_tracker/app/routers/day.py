from datetime import date, datetime
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, File, Form, Request, UploadFile
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import DailyEntry, MealEntry
from app.services.food_ai_service import estimate_food_nutrition


router = APIRouter(prefix="/day", tags=["day"])
templates = Jinja2Templates(directory="app/templates")
UPLOAD_DIR = Path("app/uploads")
TRAINING_PARTS = ["胸", "背", "腿", "肩", "手臂", "核心", "有氧", "休息"]
WEEKDAY_LABELS = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
MEAL_TYPE_LABELS = {
    "breakfast": "早餐",
    "lunch": "午餐",
    "dinner": "晚餐",
    "snack": "加餐",
    "pre_workout": "训练前",
    "post_workout": "训练后",
    "night": "夜宵",
    "custom": "自定义",
}
MEAL_TYPES = list(MEAL_TYPE_LABELS.items())


@router.get("/{entry_date}")
def day_page(
    entry_date: str,
    request: Request,
    saved: bool = False,
    db: Session = Depends(get_db),
):
    target_date = _parse_date(entry_date)
    if target_date is None:
        return RedirectResponse(url=f"/day/{date.today().isoformat()}", status_code=303)

    entry = db.query(DailyEntry).filter(DailyEntry.entry_date == target_date).first()
    meals = (
        db.query(MealEntry)
        .filter(MealEntry.entry_date == target_date)
        .order_by(MealEntry.created_at.asc(), MealEntry.id.asc())
        .all()
    )
    selected_parts = _split_training_parts(entry.training_parts if entry else None)
    return templates.TemplateResponse(
        name="day.html",
        request=request,
        context={
            "request": request,
            "entry": entry,
            "entry_date": target_date,
            "date_label": _format_date_label(target_date),
            "today": date.today(),
            "training_parts": TRAINING_PARTS,
            "selected_parts": selected_parts,
            "meals": meals,
            "meal_totals": _meal_totals(meals),
            "meal_types": MEAL_TYPES,
            "meal_type_labels": MEAL_TYPE_LABELS,
            "saved": saved,
            "active_page": "today" if target_date == date.today() else "calendar",
        },
    )


@router.post("/{entry_date}")
async def save_day(
    entry_date: str,
    weight_kg: str = Form(""),
    waist_cm: str = Form(""),
    sleep_hours: str = Form(""),
    fatigue_level: str = Form(""),
    training_parts: list[str] | None = Form(None),
    training_notes: str = Form(""),
    food_description: str = Form(""),
    calories: str = Form(""),
    protein_g: str = Form(""),
    carbs_g: str = Form(""),
    fat_g: str = Form(""),
    daily_note: str = Form(""),
    image: UploadFile | None = File(None),
    db: Session = Depends(get_db),
):
    target_date = _parse_date(entry_date)
    if target_date is None:
        return RedirectResponse(url=f"/day/{date.today().isoformat()}", status_code=303)

    entry = db.query(DailyEntry).filter(DailyEntry.entry_date == target_date).first()
    if entry is None:
        entry = DailyEntry(entry_date=target_date)
        db.add(entry)

    image_path = await _save_upload(image)
    if image_path:
        entry.image_path = image_path

    description = food_description.strip()
    should_estimate = description and any(
        not value.strip() for value in [calories, protein_g, carbs_g, fat_g]
    )
    estimate = estimate_food_nutrition(description, entry.image_path) if should_estimate else None

    entry.weight_kg = _parse_float(weight_kg)
    entry.waist_cm = _parse_float(waist_cm)
    entry.sleep_hours = _parse_float(sleep_hours)
    entry.fatigue_level = _parse_int(fatigue_level)
    entry.training_parts = ",".join(training_parts or [])
    entry.training_notes = training_notes.strip() or None
    entry.food_description = description or None
    entry.calories = _parse_float(calories, estimate.calories if estimate else None)
    entry.protein_g = _parse_float(protein_g, estimate.protein_g if estimate else None)
    entry.carbs_g = _parse_float(carbs_g, estimate.carbs_g if estimate else None)
    entry.fat_g = _parse_float(fat_g, estimate.fat_g if estimate else None)
    entry.daily_note = daily_note.strip() or None
    db.commit()

    return RedirectResponse(url=f"/day/{target_date.isoformat()}?saved=1", status_code=303)


@router.post("/{entry_date}/meals")
async def create_meal(
    entry_date: str,
    meal_type: str = Form(...),
    meal_name: str = Form(""),
    description: str = Form(...),
    calories: str = Form(""),
    protein_g: str = Form(""),
    carbs_g: str = Form(""),
    fat_g: str = Form(""),
    notes: str = Form(""),
    image: UploadFile | None = File(None),
    db: Session = Depends(get_db),
):
    target_date = _parse_date(entry_date)
    if target_date is None:
        return RedirectResponse(url=f"/day/{date.today().isoformat()}", status_code=303)

    image_path = await _save_upload(image)
    meal = MealEntry(entry_date=target_date)
    _apply_meal_form(
        meal=meal,
        meal_type=meal_type,
        meal_name=meal_name,
        description=description,
        calories=calories,
        protein_g=protein_g,
        carbs_g=carbs_g,
        fat_g=fat_g,
        notes=notes,
        image_path=image_path,
    )
    db.add(meal)
    db.commit()
    return RedirectResponse(url=f"/day/{target_date.isoformat()}?saved=1", status_code=303)


@router.post("/{entry_date}/meals/{meal_id}/update")
async def update_meal(
    entry_date: str,
    meal_id: int,
    meal_type: str = Form(...),
    meal_name: str = Form(""),
    description: str = Form(...),
    calories: str = Form(""),
    protein_g: str = Form(""),
    carbs_g: str = Form(""),
    fat_g: str = Form(""),
    notes: str = Form(""),
    image: UploadFile | None = File(None),
    db: Session = Depends(get_db),
):
    target_date = _parse_date(entry_date)
    if target_date is None:
        return RedirectResponse(url=f"/day/{date.today().isoformat()}", status_code=303)

    meal = (
        db.query(MealEntry)
        .filter(MealEntry.id == meal_id, MealEntry.entry_date == target_date)
        .first()
    )
    if meal is None:
        return RedirectResponse(url=f"/day/{target_date.isoformat()}", status_code=303)

    image_path = await _save_upload(image)
    _apply_meal_form(
        meal=meal,
        meal_type=meal_type,
        meal_name=meal_name,
        description=description,
        calories=calories,
        protein_g=protein_g,
        carbs_g=carbs_g,
        fat_g=fat_g,
        notes=notes,
        image_path=image_path,
    )
    db.commit()
    return RedirectResponse(url=f"/day/{target_date.isoformat()}?saved=1", status_code=303)


@router.post("/{entry_date}/meals/{meal_id}/delete")
def delete_meal(entry_date: str, meal_id: int, db: Session = Depends(get_db)):
    target_date = _parse_date(entry_date)
    if target_date is None:
        return RedirectResponse(url=f"/day/{date.today().isoformat()}", status_code=303)

    meal = (
        db.query(MealEntry)
        .filter(MealEntry.id == meal_id, MealEntry.entry_date == target_date)
        .first()
    )
    if meal is not None:
        db.delete(meal)
        db.commit()
    return RedirectResponse(url=f"/day/{target_date.isoformat()}?saved=1", status_code=303)


def _parse_date(value: str) -> date | None:
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        return None


def _format_date_label(value: date) -> str:
    return f"{value.month} 月 {value.day} 日 {WEEKDAY_LABELS[value.weekday()]}"


def _split_training_parts(value: str | None) -> list[str]:
    if not value:
        return []
    return [part for part in value.split(",") if part]


def _meal_totals(meals: list[MealEntry]) -> dict[str, float]:
    return {
        "calories": round(sum(meal.calories or 0 for meal in meals), 1),
        "protein_g": round(sum(meal.protein_g or 0 for meal in meals), 1),
        "carbs_g": round(sum(meal.carbs_g or 0 for meal in meals), 1),
        "fat_g": round(sum(meal.fat_g or 0 for meal in meals), 1),
    }


def _apply_meal_form(
    meal: MealEntry,
    meal_type: str,
    meal_name: str,
    description: str,
    calories: str,
    protein_g: str,
    carbs_g: str,
    fat_g: str,
    notes: str,
    image_path: str | None,
):
    clean_description = description.strip()
    estimate = estimate_food_nutrition(clean_description, image_path or meal.image_path)

    meal.meal_type = meal_type if meal_type in MEAL_TYPE_LABELS else "custom"
    meal.meal_name = meal_name.strip() or None
    meal.description = clean_description
    if image_path:
        meal.image_path = image_path
    meal.calories = _parse_float(calories, estimate.calories) or 0
    meal.protein_g = _parse_float(protein_g, estimate.protein_g) or 0
    meal.carbs_g = _parse_float(carbs_g, estimate.carbs_g) or 0
    meal.fat_g = _parse_float(fat_g, estimate.fat_g) or 0
    meal.notes = notes.strip() or None


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


def _parse_float(value: str, default: float | None = None) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _parse_int(value: str) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None
