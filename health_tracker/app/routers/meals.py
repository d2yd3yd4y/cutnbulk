from datetime import date

from fastapi import APIRouter, Depends, File, Form, Request, UploadFile
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.constants import MEAL_TYPE_LABELS
from app.database import get_db
from app.models import MealEntry
from app.services.food_ai_service import TEMPLATE_ESTIMATES, estimate_food_nutrition
from app.services.upload_service import save_upload
from app.utils.form_parsing import parse_float
from app.utils.meal_totals import meal_totals


router = APIRouter(prefix="/meals", tags=["meals"])
templates = Jinja2Templates(directory="app/templates")


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

    return templates.TemplateResponse(
        name="meals.html",
        request=request,
        context={
            "request": request,
            "today": today,
            "meals": meals,
            "totals": meal_totals(today_meals),
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
    image_path = await save_upload(image)
    estimate = estimate_food_nutrition(description, image_path)

    meal = MealEntry(
        entry_date=entry_date,
        meal_type=meal_type,
        description=description.strip(),
        image_path=image_path,
        calories=parse_float(calories, estimate.calories) or 0,
        protein_g=parse_float(protein_g, estimate.protein_g) or 0,
        carbs_g=parse_float(carbs_g, estimate.carbs_g) or 0,
        fat_g=parse_float(fat_g, estimate.fat_g) or 0,
        notes=notes,
    )
    db.add(meal)
    db.commit()
    return RedirectResponse(url="/meals", status_code=303)
