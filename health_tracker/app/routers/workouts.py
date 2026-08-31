from datetime import date

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import WorkoutEntry
from app.utils.form_parsing import parse_float, parse_int


router = APIRouter(prefix="/workouts", tags=["workouts"])
templates = Jinja2Templates(directory="app/templates")


@router.get("")
@router.get("/")
def workouts_page(request: Request, db: Session = Depends(get_db)):
    today = date.today()
    entries = (
        db.query(WorkoutEntry)
        .order_by(WorkoutEntry.entry_date.desc(), WorkoutEntry.created_at.desc())
        .limit(100)
        .all()
    )
    today_entries = db.query(WorkoutEntry).filter(WorkoutEntry.entry_date == today).all()
    totals = {
        "sets": sum(entry.sets for entry in today_entries),
        "volume": round(sum(entry.volume for entry in today_entries), 1),
    }

    return templates.TemplateResponse(
        name="workouts.html",
        request=request,
        context={
            "request": request,
            "today": today,
            "entries": entries,
            "totals": totals,
            "active_page": "workouts",
        },
    )


@router.post("")
@router.post("/")
def create_workouts(
    entry_date: date = Form(...),
    exercise: list[str] = Form(...),
    sets: list[str] = Form(...),
    reps: list[str] = Form(...),
    weight_kg: list[str] = Form(...),
    rpe: list[str] = Form(...),
    to_failure: list[str] | None = Form(None),
    notes: list[str] = Form(...),
    db: Session = Depends(get_db),
):
    failure_indexes = {int(index) for index in (to_failure or []) if str(index).isdigit()}
    for index, name in enumerate(exercise):
        clean_name = name.strip()
        if not clean_name:
            continue
        entry = WorkoutEntry(
            entry_date=entry_date,
            exercise=clean_name,
            sets=parse_int(_get(sets, index), default=0),
            reps=parse_int(_get(reps, index), default=0),
            weight_kg=parse_float(_get(weight_kg, index), default=0),
            rpe=parse_int(_get(rpe, index), default=None),
            to_failure=index in failure_indexes,
            notes=_get(notes, index).strip() or None,
        )
        db.add(entry)
    db.commit()
    return RedirectResponse(url="/workouts", status_code=303)


def _get(values: list[str], index: int) -> str:
    return values[index] if index < len(values) else ""
