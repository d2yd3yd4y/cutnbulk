import json
from datetime import date, datetime
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, File, Form, Request, UploadFile
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import DailyEntry, MealEntry, MealFoodMatch
from app.services.goal_service import get_goal_progress_for_day
from app.services.nutrition_estimator import NutritionEstimateResult, estimate_meal_nutrition
from app.services.vision_food_estimator import estimate_food_from_image


router = APIRouter(prefix="/day", tags=["day"])
templates = Jinja2Templates(directory="app/templates")
UPLOAD_DIR = Path("app/uploads")
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
MEAL_ERROR_MESSAGES = {
    "photo_required": "拍照估算需要上传照片。",
    "description_required": "手动输入需要填写食物描述。",
    "upload_failed": "照片上传失败，请重试。",
}


@router.get("/{entry_date}")
def day_page(
    entry_date: str,
    request: Request,
    saved: bool = False,
    error: str | None = None,
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
    meal_matches = (
        db.query(MealFoodMatch)
        .filter(MealFoodMatch.meal_entry_id.in_([meal.id for meal in meals] or [0]))
        .order_by(MealFoodMatch.id.asc())
        .all()
    )
    matches_by_meal: dict[int, list[MealFoodMatch]] = {}
    for match in meal_matches:
        matches_by_meal.setdefault(match.meal_entry_id, []).append(match)
    uncertainty_by_meal = {
        meal.id: _parse_uncertainty_factors(meal.uncertainty_factors) for meal in meals
    }
    return templates.TemplateResponse(
        name="day.html",
        request=request,
        context={
            "request": request,
            "entry": entry,
            "entry_date": target_date,
            "date_label": _format_date_label(target_date),
            "today": date.today(),
            "meals": meals,
            "meal_totals": _meal_totals(meals),
            "matches_by_meal": matches_by_meal,
            "uncertainty_by_meal": uncertainty_by_meal,
            "goal_progress": get_goal_progress_for_day(db, target_date),
            "meal_types": MEAL_TYPES,
            "meal_type_labels": MEAL_TYPE_LABELS,
            "saved": saved,
            "error_message": MEAL_ERROR_MESSAGES.get(error or "", None),
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
    daily_note: str = Form(""),
    db: Session = Depends(get_db),
):
    target_date = _parse_date(entry_date)
    if target_date is None:
        return RedirectResponse(url=f"/day/{date.today().isoformat()}", status_code=303)

    entry = db.query(DailyEntry).filter(DailyEntry.entry_date == target_date).first()
    if entry is None:
        entry = DailyEntry(entry_date=target_date)
        db.add(entry)

    # Keep legacy training_parts / training_notes untouched so old data stays intact.
    entry.weight_kg = _parse_float(weight_kg)
    entry.waist_cm = _parse_float(waist_cm)
    entry.sleep_hours = _parse_float(sleep_hours)
    entry.fatigue_level = _parse_int(fatigue_level)
    entry.daily_note = daily_note.strip() or None
    db.commit()

    return RedirectResponse(url=f"/day/{target_date.isoformat()}?saved=1", status_code=303)


@router.post("/{entry_date}/meals")
async def create_meal(
    entry_date: str,
    meal_type: str = Form(...),
    meal_name: str = Form(""),
    description: str = Form(""),
    calories: str = Form(""),
    protein_g: str = Form(""),
    carbs_g: str = Form(""),
    fat_g: str = Form(""),
    notes: str = Form(""),
    entry_mode: str = Form("manual"),
    image: UploadFile | None = File(None),
    db: Session = Depends(get_db),
):
    target_date = _parse_date(entry_date)
    if target_date is None:
        return RedirectResponse(url=f"/day/{date.today().isoformat()}", status_code=303)

    mode = _normalize_entry_mode(entry_mode)
    image_path, upload_error = await _save_upload(image)
    if upload_error:
        return RedirectResponse(
            url=f"/day/{target_date.isoformat()}?error=upload_failed#add-meal",
            status_code=303,
        )

    if mode == "photo":
        if not image_path:
            return RedirectResponse(
                url=f"/day/{target_date.isoformat()}?error=photo_required#add-meal",
                status_code=303,
            )
        calories = protein_g = carbs_g = fat_g = ""
        prefer_vision = True
    else:
        image_path = None
        prefer_vision = False
        if not description.strip():
            return RedirectResponse(
                url=f"/day/{target_date.isoformat()}?error=description_required#add-meal",
                status_code=303,
            )

    meal = MealEntry(entry_date=target_date)
    estimate = _apply_meal_form(
        db=db,
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
        prefer_vision=prefer_vision,
        entry_mode=mode,
    )
    db.add(meal)
    db.flush()
    _sync_meal_matches(db, meal, estimate)
    db.commit()
    return RedirectResponse(url=f"/day/{target_date.isoformat()}?saved=1", status_code=303)


@router.post("/{entry_date}/meals/{meal_id}/update")
async def update_meal(
    entry_date: str,
    meal_id: int,
    meal_type: str = Form(...),
    meal_name: str = Form(""),
    description: str = Form(""),
    calories: str = Form(""),
    protein_g: str = Form(""),
    carbs_g: str = Form(""),
    fat_g: str = Form(""),
    notes: str = Form(""),
    entry_mode: str = Form("manual"),
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

    mode = _normalize_entry_mode(entry_mode)
    image_path, upload_error = await _save_upload(image)
    if upload_error:
        return RedirectResponse(
            url=f"/day/{target_date.isoformat()}?error=upload_failed",
            status_code=303,
        )

    if mode == "photo":
        if not image_path and not meal.image_path:
            return RedirectResponse(
                url=f"/day/{target_date.isoformat()}?error=photo_required",
                status_code=303,
            )
        if image_path:
            calories = protein_g = carbs_g = fat_g = ""
            prefer_vision = True
            preserve_estimate = False
        else:
            # Keep existing AI/fallback nutrition when user doesn't re-upload.
            prefer_vision = False
            preserve_estimate = True
    else:
        image_path = None
        prefer_vision = False
        preserve_estimate = False
        if not description.strip():
            return RedirectResponse(
                url=f"/day/{target_date.isoformat()}?error=description_required",
                status_code=303,
            )

    estimate = _apply_meal_form(
        db=db,
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
        prefer_vision=prefer_vision,
        entry_mode=mode,
        preserve_estimate=preserve_estimate,
    )
    if not preserve_estimate:
        _sync_meal_matches(db, meal, estimate)
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


def _meal_totals(meals: list[MealEntry]) -> dict[str, float]:
    return {
        "calories": round(sum(meal.calories or 0 for meal in meals), 1),
        "protein_g": round(sum(meal.protein_g or 0 for meal in meals), 1),
        "carbs_g": round(sum(meal.carbs_g or 0 for meal in meals), 1),
        "fat_g": round(sum(meal.fat_g or 0 for meal in meals), 1),
    }


def _normalize_entry_mode(value: str) -> str:
    return value if value in {"manual", "photo"} else "manual"


def _apply_meal_form(
    db: Session,
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
    prefer_vision: bool = False,
    entry_mode: str = "manual",
    preserve_estimate: bool = False,
):
    clean_description = description.strip()
    resolved_image = image_path or meal.image_path

    meal.meal_type = meal_type if meal_type in MEAL_TYPE_LABELS else "custom"
    if meal.meal_type == "custom":
        meal.meal_name = meal_name.strip() or None
    else:
        meal.meal_name = None

    if clean_description:
        meal.description = clean_description
    elif not meal.description:
        meal.description = "拍照餐食"

    if image_path:
        meal.image_path = image_path

    meal.notes = notes.strip() or None

    if preserve_estimate:
        return NutritionEstimateResult(
            dish_name=None,
            calories=meal.calories or 0,
            protein_g=meal.protein_g or 0,
            carbs_g=meal.carbs_g or 0,
            fat_g=meal.fat_g or 0,
            confidence=meal.estimate_confidence or 0.5,
            confidence_label="medium",
            reasoning=meal.estimate_reasoning or "",
            matched_foods=[],
            source=meal.estimate_source or "fallback",
            calorie_range_low=meal.calorie_range_low,
            calorie_range_high=meal.calorie_range_high,
            uncertainty_factors=_parse_uncertainty_factors(meal.uncertainty_factors),
        )

    if prefer_vision:
        estimate = estimate_food_from_image(db, resolved_image, clean_description)
    elif clean_description:
        estimate = estimate_meal_nutrition(db, clean_description, resolved_image)
    else:
        estimate = NutritionEstimateResult(
            dish_name=None,
            calories=0,
            protein_g=0,
            carbs_g=0,
            fat_g=0,
            confidence=0.2,
            confidence_label="low",
            reasoning="未提供足够信息，请补充描述或照片。",
            matched_foods=[],
            source="fallback",
            calorie_range_low=0,
            calorie_range_high=0,
            uncertainty_factors=["缺少描述"],
        )

    if not clean_description and getattr(estimate, "dish_name", None):
        meal.description = estimate.dish_name

    meal.calories = _parse_float(calories, estimate.calories) or 0
    meal.protein_g = _parse_float(protein_g, estimate.protein_g) or 0
    meal.carbs_g = _parse_float(carbs_g, estimate.carbs_g) or 0
    meal.fat_g = _parse_float(fat_g, estimate.fat_g) or 0

    if entry_mode == "manual" and _all_manual_nutrition(calories, protein_g, carbs_g, fat_g):
        meal.estimate_source = "manual"
        meal.estimate_confidence = 1.0
        meal.estimate_reasoning = "用户手动填写营养数据。"
        meal.calorie_range_low = meal.calories
        meal.calorie_range_high = meal.calories
        meal.uncertainty_factors = json.dumps([], ensure_ascii=False)
    else:
        meal.estimate_confidence = estimate.confidence
        meal.estimate_reasoning = estimate.reasoning
        meal.estimate_source = estimate.source
        meal.calorie_range_low = estimate.calorie_range_low
        meal.calorie_range_high = estimate.calorie_range_high
        meal.uncertainty_factors = json.dumps(estimate.uncertainty_factors or [], ensure_ascii=False)

    return estimate


def _sync_meal_matches(db: Session, meal: MealEntry, estimate: NutritionEstimateResult):
    db.query(MealFoodMatch).filter(MealFoodMatch.meal_entry_id == meal.id).delete()
    for match in estimate.matched_foods:
        db.add(
            MealFoodMatch(
                meal_entry_id=meal.id,
                food_item_id=match.food_item_id,
                matched_text=match.matched_text,
                estimated_grams=match.estimated_grams,
                calories=match.calories,
                protein_g=match.protein_g,
                carbs_g=match.carbs_g,
                fat_g=match.fat_g,
                confidence=match.confidence,
            )
        )


async def _save_upload(image: UploadFile | None) -> tuple[str | None, str | None]:
    if not image or not image.filename:
        return None, None

    content = await image.read()
    if not content:
        return None, "empty"

    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    suffix = Path(image.filename).suffix.lower() or ".jpg"
    if suffix not in {".jpg", ".jpeg", ".png", ".webp", ".gif", ".heic", ".heif"}:
        suffix = ".jpg"
    filename = f"{uuid4().hex}{suffix}"
    destination = UPLOAD_DIR / filename
    destination.write_bytes(content)
    return f"/uploads/{filename}", None


def _parse_float(value: str, default: float | None = None) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _has_manual_nutrition(*values: str) -> bool:
    return any((value or "").strip() for value in values)


def _all_manual_nutrition(*values: str) -> bool:
    return all((value or "").strip() for value in values)


def _parse_uncertainty_factors(value: str | None) -> list[str]:
    if not value:
        return []
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError:
        return []
    return parsed if isinstance(parsed, list) else []


def _parse_int(value: str) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None
