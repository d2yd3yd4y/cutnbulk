from datetime import date

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import GoalSetting
from app.services.goal_service import (
    ACTIVITY_LABELS,
    MODE_LABELS,
    calculate_goal,
    get_active_goal,
    validate_goal,
)


router = APIRouter(prefix="/goal", tags=["goal"])
templates = Jinja2Templates(directory="app/templates")


@router.get("")
@router.get("/")
def goal_page(request: Request, db: Session = Depends(get_db)):
    goal = get_active_goal(db)
    return templates.TemplateResponse(
        name="goal.html",
        request=request,
        context={
            "request": request,
            "today": date.today(),
            "goal": goal,
            "mode_labels": MODE_LABELS,
            "activity_labels": ACTIVITY_LABELS,
            "error": None,
            "form_values": {},
            "active_page": "calendar",
        },
    )


@router.post("")
@router.post("/")
def save_goal(
    request: Request,
    mode: str = Form(...),
    current_weight_kg: str = Form(...),
    target_weight_kg: str = Form(...),
    target_days: str = Form(...),
    activity_level: str = Form("moderate"),
    maintenance_calories: str = Form(""),
    db: Session = Depends(get_db),
):
    form_values = {
        "mode": mode,
        "current_weight_kg": current_weight_kg,
        "target_weight_kg": target_weight_kg,
        "target_days": target_days,
        "activity_level": activity_level,
        "maintenance_calories": maintenance_calories,
    }
    try:
        current = float(current_weight_kg)
        target = float(target_weight_kg)
        days = int(target_days)
        maintenance = float(maintenance_calories) if maintenance_calories.strip() else None
    except ValueError:
        return _goal_form_response(request, db, "请填写有效的数字。", form_values)

    error = validate_goal(mode, current, target, days)
    if error:
        return _goal_form_response(request, db, error, form_values)

    calculation = calculate_goal(
        mode=mode,
        current_weight_kg=current,
        target_weight_kg=target,
        target_days=days,
        activity_level=activity_level,
        maintenance_calories=maintenance,
    )

    goal = get_active_goal(db)
    if goal is None:
        goal = GoalSetting(is_active=True)
        db.add(goal)

    goal.mode = calculation.mode
    goal.current_weight_kg = calculation.current_weight_kg
    goal.target_weight_kg = calculation.target_weight_kg
    goal.target_days = calculation.target_days
    goal.activity_level = calculation.activity_level
    goal.maintenance_calories = calculation.maintenance_calories
    goal.recommended_calories = calculation.recommended_calories
    goal.daily_energy_delta = calculation.daily_energy_delta
    goal.weekly_weight_change = calculation.weekly_weight_change
    goal.note = calculation.note
    goal.is_active = True
    db.commit()
    return RedirectResponse(url="/", status_code=303)


def _goal_form_response(
    request: Request,
    db: Session,
    error: str,
    form_values: dict[str, str],
):
    return templates.TemplateResponse(
        name="goal.html",
        request=request,
        context={
            "request": request,
            "today": date.today(),
            "goal": get_active_goal(db),
            "mode_labels": MODE_LABELS,
            "activity_labels": ACTIVITY_LABELS,
            "error": error,
            "form_values": form_values,
            "active_page": "calendar",
        },
        status_code=400,
    )
