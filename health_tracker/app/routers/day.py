import json
from datetime import date, datetime
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import CurrentUser
from app.models import DailyEntry, MealEntry, MealFoodMatch
from app.security.csrf import validate_csrf
from app.services.goal_service import get_goal_progress_for_day
from app.services.nutrition_estimator import NutritionEstimateResult, estimate_meal_nutrition
from app.services.storage import StorageError, storage_service
from app.services.vision_food_estimator import estimate_food_from_image
from app.templating import render


router = APIRouter(prefix="/day", tags=["day"])
WEEKDAY_LABELS = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
MEAL_TYPE_LABELS = {
    "breakfast": "早餐",
    "lunch": "午餐",
    "dinner": "晚餐",
    "snack": "加餐",
    "night": "夜宵",
    "custom": "自定义",
}
MEAL_TYPES = list(MEAL_TYPE_LABELS.items())


@router.get("/{entry_date}")
def day_page(
    entry_date: str,
    request: Request,
    user: CurrentUser,
    saved: bool = False,
    db: Session = Depends(get_db),
):
    target_date = _parse_date(entry_date)
    if target_date is None:
        return RedirectResponse(url=f"/day/{date.today().isoformat()}", status_code=303)

    entry = (
        db.query(DailyEntry)
        .filter(DailyEntry.user_id == user.id, DailyEntry.entry_date == target_date)
        .first()
    )
    meals = (
        db.query(MealEntry)
        .filter(MealEntry.user_id == user.id, MealEntry.entry_date == target_date)
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
    return render(
        request,
        "day.html",
        {
            "entry": entry,
            "entry_date": target_date,
            "date_label": _format_date_label(target_date),
            "today": date.today(),
            "meals": meals,
            "meal_totals": _meal_totals(meals),
            "matches_by_meal": matches_by_meal,
            "uncertainty_by_meal": uncertainty_by_meal,
            "goal_progress": get_goal_progress_for_day(db, user.id, target_date),
            "meal_types": MEAL_TYPES,
            "meal_type_labels": MEAL_TYPE_LABELS,
            "saved": saved,
            "active_page": "today" if target_date == date.today() else "calendar",
        },
        user=user,
    )


@router.post("/{entry_date}")
async def save_day(
    entry_date: str,
    request: Request,
    user: CurrentUser,
    weight_kg: str = Form(""),
    waist_cm: str = Form(""),
    sleep_hours: str = Form(""),
    fatigue_level: str = Form(""),
    daily_note: str = Form(""),
    csrf_token: str = Form(""),
    db: Session = Depends(get_db),
):
    validate_csrf(request, csrf_token)
    target_date = _parse_date(entry_date)
    if target_date is None:
        return RedirectResponse(url=f"/day/{date.today().isoformat()}", status_code=303)

    entry = (
        db.query(DailyEntry)
        .filter(DailyEntry.user_id == user.id, DailyEntry.entry_date == target_date)
        .first()
    )
    if entry is None:
        entry = DailyEntry(user_id=user.id, entry_date=target_date)
        db.add(entry)

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
    request: Request,
    user: CurrentUser,
    meal_type: str = Form(...),
    meal_name: str = Form(""),
    description: str = Form(""),
    calories: str = Form(""),
    protein_g: str = Form(""),
    carbs_g: str = Form(""),
    fat_g: str = Form(""),
    notes: str = Form(""),
    csrf_token: str = Form(""),
    image: UploadFile | None = File(None),
    db: Session = Depends(get_db),
):
    validate_csrf(request, csrf_token)
    target_date = _parse_date(entry_date)
    if target_date is None:
        return RedirectResponse(url=f"/day/{date.today().isoformat()}", status_code=303)

    try:
        image_key = await _save_upload(user.id, image)
    except StorageError as exc:
        return RedirectResponse(
            url=f"/day/{target_date.isoformat()}?saved=0",
            status_code=303,
            headers={"X-Error": exc.message},
        )

    if not description.strip() and not image_key:
        return RedirectResponse(url=f"/day/{target_date.isoformat()}", status_code=303)

    meal = MealEntry(user_id=user.id, entry_date=target_date)
    try:
        estimate = _apply_meal_form(
            db=db,
            user_id=user.id,
            meal=meal,
            meal_type=meal_type,
            meal_name=meal_name,
            description=description,
            calories=calories,
            protein_g=protein_g,
            carbs_g=carbs_g,
            fat_g=fat_g,
            notes=notes,
            image_path=image_key,
            prefer_vision=bool(image_key) and not _has_manual_nutrition(calories, protein_g, carbs_g, fat_g),
        )
        db.add(meal)
        db.flush()
        _sync_meal_matches(db, meal, estimate)
        db.commit()
    except Exception:
        if image_key:
            storage_service.delete_object(image_key)
        raise
    return RedirectResponse(url=f"/day/{target_date.isoformat()}?saved=1", status_code=303)


@router.post("/{entry_date}/meals/{meal_id}/update")
async def update_meal(
    entry_date: str,
    meal_id: int,
    request: Request,
    user: CurrentUser,
    meal_type: str = Form(...),
    meal_name: str = Form(""),
    description: str = Form(""),
    calories: str = Form(""),
    protein_g: str = Form(""),
    carbs_g: str = Form(""),
    fat_g: str = Form(""),
    notes: str = Form(""),
    csrf_token: str = Form(""),
    image: UploadFile | None = File(None),
    db: Session = Depends(get_db),
):
    validate_csrf(request, csrf_token)
    target_date = _parse_date(entry_date)
    if target_date is None:
        return RedirectResponse(url=f"/day/{date.today().isoformat()}", status_code=303)

    meal = (
        db.query(MealEntry)
        .filter(
            MealEntry.id == meal_id,
            MealEntry.user_id == user.id,
            MealEntry.entry_date == target_date,
        )
        .first()
    )
    if meal is None:
        raise HTTPException(status_code=404, detail="Not Found")

    old_image = meal.image_path
    image_key = None
    try:
        image_key = await _save_upload(user.id, image)
    except StorageError:
        return RedirectResponse(url=f"/day/{target_date.isoformat()}", status_code=303)

    if not description.strip() and not image_key and not meal.image_path:
        return RedirectResponse(url=f"/day/{target_date.isoformat()}", status_code=303)

    try:
        estimate = _apply_meal_form(
            db=db,
            user_id=user.id,
            meal=meal,
            meal_type=meal_type,
            meal_name=meal_name,
            description=description,
            calories=calories,
            protein_g=protein_g,
            carbs_g=carbs_g,
            fat_g=fat_g,
            notes=notes,
            image_path=image_key,
            prefer_vision=bool(image_key) and not _has_manual_nutrition(calories, protein_g, carbs_g, fat_g),
        )
        _sync_meal_matches(db, meal, estimate)
        db.commit()
    except Exception:
        if image_key:
            storage_service.delete_object(image_key)
        raise

    if image_key and old_image and old_image != image_key:
        storage_service.delete_object(old_image)
    return RedirectResponse(url=f"/day/{target_date.isoformat()}?saved=1", status_code=303)


@router.post("/{entry_date}/meals/{meal_id}/delete")
def delete_meal(
    entry_date: str,
    meal_id: int,
    request: Request,
    user: CurrentUser,
    csrf_token: str = Form(""),
    db: Session = Depends(get_db),
):
    validate_csrf(request, csrf_token)
    target_date = _parse_date(entry_date)
    if target_date is None:
        return RedirectResponse(url=f"/day/{date.today().isoformat()}", status_code=303)

    meal = (
        db.query(MealEntry)
        .filter(
            MealEntry.id == meal_id,
            MealEntry.user_id == user.id,
            MealEntry.entry_date == target_date,
        )
        .first()
    )
    if meal is None:
        raise HTTPException(status_code=404, detail="Not Found")

    image_key = meal.image_path
    db.query(MealFoodMatch).filter(MealFoodMatch.meal_entry_id == meal.id).delete()
    db.delete(meal)
    db.commit()
    storage_service.delete_object(image_key)
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


def _apply_meal_form(
    db: Session,
    user_id: str,
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
):
    clean_description = description.strip()
    manual = _has_manual_nutrition(calories, protein_g, carbs_g, fat_g)

    if manual:
        estimate = NutritionEstimateResult(
            dish_name=clean_description or meal.description or "手动记录",
            calories=_parse_float(calories, 0) or 0,
            protein_g=_parse_float(protein_g, 0) or 0,
            carbs_g=_parse_float(carbs_g, 0) or 0,
            fat_g=_parse_float(fat_g, 0) or 0,
            confidence=1.0,
            confidence_label="high",
            reasoning="已使用手动填写的营养数字。",
            matched_foods=[],
            source="manual",
        )
    elif prefer_vision:
        estimate = estimate_food_from_image(db, image_path or meal.image_path, clean_description, user_id=user_id)
    elif clean_description:
        estimate = estimate_meal_nutrition(db, clean_description, None, user_id=user_id)
    else:
        estimate = NutritionEstimateResult(
            dish_name="（未估算）",
            calories=0,
            protein_g=0,
            carbs_g=0,
            fat_g=0,
            confidence=0,
            confidence_label="low",
            reasoning="未填写营养数字且无法估算。",
            matched_foods=[],
            source="none",
        )

    meal.meal_type = meal_type if meal_type in MEAL_TYPE_LABELS else "custom"
    meal.meal_name = meal_name.strip() or None
    if clean_description:
        meal.description = clean_description
    elif estimate.dish_name:
        meal.description = estimate.dish_name
    elif not meal.description:
        meal.description = "（拍照估算）"
    if image_path:
        meal.image_path = image_path
    meal.calories = _parse_float(calories, estimate.calories) or 0
    meal.protein_g = _parse_float(protein_g, estimate.protein_g) or 0
    meal.carbs_g = _parse_float(carbs_g, estimate.carbs_g) or 0
    meal.fat_g = _parse_float(fat_g, estimate.fat_g) or 0
    meal.estimate_confidence = estimate.confidence
    meal.estimate_reasoning = estimate.reasoning
    meal.estimate_source = estimate.source
    meal.calorie_range_low = estimate.calorie_range_low
    meal.calorie_range_high = estimate.calorie_range_high
    meal.uncertainty_factors = json.dumps(estimate.uncertainty_factors or [], ensure_ascii=False)
    meal.notes = notes.strip() or None
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


async def _save_upload(user_id: str, image: UploadFile | None) -> str | None:
    if not image or not image.filename:
        return None
    content = await image.read()
    if not content:
        return None
    return storage_service.save_meal_image(user_id, content, image.filename)


def _parse_float(value: str, default: float | None = None) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _has_manual_nutrition(*values: str) -> bool:
    return any(value.strip() for value in values)


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
