from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import CurrentUser
from app.models import MealEntry
from app.services.storage import storage_service


router = APIRouter(tags=["media"])


@router.get("/media/meals/{meal_id}")
def meal_image(meal_id: int, user: CurrentUser, db: Session = Depends(get_db)):
    meal = (
        db.query(MealEntry)
        .filter(MealEntry.id == meal_id, MealEntry.user_id == user.id)
        .first()
    )
    if meal is None or not meal.image_path:
        raise HTTPException(status_code=404, detail="Not Found")

    signed = storage_service.create_signed_url(meal.image_path)
    if signed:
        return RedirectResponse(url=signed, status_code=302)

    path = storage_service.open_local_file(meal.image_path)
    if path is None:
        raise HTTPException(status_code=404, detail="Not Found")
    return FileResponse(path, media_type="image/jpeg")
