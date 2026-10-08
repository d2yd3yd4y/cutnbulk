import json
from datetime import date

from fastapi import APIRouter, Depends, Form, Query, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import FoodItem
from app.services.food_seed_service import normalize_food_name


router = APIRouter(prefix="/foods", tags=["foods"])
templates = Jinja2Templates(directory="app/templates")


@router.get("")
@router.get("/")
def foods_page(
    request: Request,
    q: str = Query(""),
    db: Session = Depends(get_db),
):
    query = db.query(FoodItem)
    if q.strip():
        normalized = normalize_food_name(q)
        like = f"%{q.strip()}%"
        normalized_like = f"%{normalized}%"
        query = query.filter(
            or_(
                FoodItem.name.contains(q.strip()),
                FoodItem.normalized_name.contains(normalized),
                FoodItem.aliases.contains(q.strip()),
                FoodItem.aliases.contains(normalized),
                FoodItem.category.like(like),
                FoodItem.cuisine.like(like),
                FoodItem.normalized_name.like(normalized_like),
            )
        )
    foods = query.order_by(FoodItem.category.asc(), FoodItem.name.asc()).limit(120).all()
    total_count = db.query(FoodItem).count()
    return templates.TemplateResponse(
        name="foods.html",
        request=request,
        context={
            "request": request,
            "today": date.today(),
            "foods": foods,
            "q": q,
            "total_count": total_count,
            "active_page": "foods",
        },
    )


@router.get("/new")
def new_food_page(request: Request):
    return templates.TemplateResponse(
        name="food_new.html",
        request=request,
        context={
            "request": request,
            "today": date.today(),
            "error": None,
            "form_values": {},
            "active_page": "foods",
        },
    )


@router.post("/new")
def create_food(
    request: Request,
    name: str = Form(...),
    aliases: str = Form(""),
    category: str = Form("自定义"),
    cuisine: str = Form(""),
    serving_desc: str = Form("100g"),
    serving_grams: str = Form("100"),
    calories_per_100g: str = Form(...),
    protein_per_100g: str = Form(...),
    carbs_per_100g: str = Form(...),
    fat_per_100g: str = Form(...),
    notes: str = Form(""),
    db: Session = Depends(get_db),
):
    form_values = {
        "name": name,
        "aliases": aliases,
        "category": category,
        "cuisine": cuisine,
        "serving_desc": serving_desc,
        "serving_grams": serving_grams,
        "calories_per_100g": calories_per_100g,
        "protein_per_100g": protein_per_100g,
        "carbs_per_100g": carbs_per_100g,
        "fat_per_100g": fat_per_100g,
        "notes": notes,
    }
    try:
        serving = float(serving_grams)
        calories = float(calories_per_100g)
        protein = float(protein_per_100g)
        carbs = float(carbs_per_100g)
        fat = float(fat_per_100g)
    except ValueError:
        return _food_form_response(request, "请填写有效的营养数字。", form_values)

    normalized = normalize_food_name(name)
    if db.query(FoodItem).filter(FoodItem.normalized_name == normalized).first():
        return _food_form_response(request, "这个食物已经存在。", form_values)

    alias_list = [alias.strip() for alias in aliases.split(",") if alias.strip()]
    db.add(
        FoodItem(
            name=name.strip(),
            normalized_name=normalized,
            aliases=json.dumps(alias_list, ensure_ascii=False),
            category=category.strip() or "自定义",
            cuisine=cuisine.strip() or "自定义",
            serving_desc=serving_desc.strip() or "100g",
            serving_grams=serving,
            calories_per_100g=calories,
            protein_per_100g=protein,
            carbs_per_100g=carbs,
            fat_per_100g=fat,
            source="user",
            confidence=0.85,
            notes=notes.strip() or None,
        )
    )
    db.commit()
    return RedirectResponse(url=f"/foods?q={name.strip()}", status_code=303)


def _food_form_response(request: Request, error: str, form_values: dict[str, str]):
    return templates.TemplateResponse(
        name="food_new.html",
        request=request,
        context={
            "request": request,
            "today": date.today(),
            "error": error,
            "form_values": form_values,
            "active_page": "foods",
        },
        status_code=400,
    )
