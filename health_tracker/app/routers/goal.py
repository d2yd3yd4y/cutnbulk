from datetime import date

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import CurrentUser
from app.models import GoalSetting
from app.security.csrf import validate_csrf
from app.services.goal_service import (
    ACTIVITY_LABELS,
    MODE_LABELS,
    calculate_goal,
    get_active_goal,
    validate_goal,
)
from app.templating import render


router = APIRouter(prefix="/goal", tags=["goal"])


@router.get("")
@router.get("/")
def goal_page(request: Request, user: CurrentUser, db: Session = Depends(get_db)):
    goal = get_active_goal(db, user.id)
    return render(
        request,
        "goal.html",
        {
            "today": date.today(),
            "goal": goal,
            "mode_labels": MODE_LABELS,
            "activity_labels": ACTIVITY_LABELS,
            "error": None,
            "form_values": {},
            "active_page": "calendar",
        },
        user=user,
    )


@router.post("")
@router.post("/")
def save_goal(
    request: Request,
    user: CurrentUser,
    mode: str = Form(...),
    current_weight_kg: str = Form(...),
    target_weight_kg: str = Form(...),
    target_days: str = Form(...),
    activity_level: str = Form("moderate"),
    maintenance_calories: str = Form(""),
    csrf_token: str = Form(""),
    db: Session = Depends(get_db),
):
    validate_csrf(request, csrf_token)
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
        return _goal_form_response(request, db, user, "请填写有效的数字。", form_values)

    error = validate_goal(mode, current, target, days)
    if error:
        return _goal_form_response(request, db, user, error, form_values)

    calculation = calculate_goal(
        mode=mode,
        current_weight_kg=current,
        target_weight_kg=target,
        target_days=days,
        activity_level=activity_level,
        maintenance_calories=maintenance,
    )

    # Deactivate previous active goals for this user.
    db.query(GoalSetting).filter(
        GoalSetting.user_id == user.id,
        GoalSetting.is_active.is_(True),
    ).update({"is_active": False})

    goal = GoalSetting(user_id=user.id, is_active=True)
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


def _goal_form_response(request, db, user, error: str, form_values: dict[str, str]):
    return render(
        request,
        "goal.html",
        {
            "today": date.today(),
            "goal": get_active_goal(db, user.id),
            "mode_labels": MODE_LABELS,
            "activity_labels": ACTIVITY_LABELS,
            "error": error,
            "form_values": form_values,
            "active_page": "calendar",
        },
        user=user,
        status_code=400,
    )
