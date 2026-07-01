from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.database import Base, engine
from app.routers import body, calendar, day, meals, summary, weekly, workouts


Base.metadata.create_all(bind=engine)

app = FastAPI(title="cutnbulk")

app.mount("/static", StaticFiles(directory="app/static"), name="static")
app.mount("/uploads", StaticFiles(directory="app/uploads"), name="uploads")

app.include_router(calendar.router)
app.include_router(day.router)
app.include_router(summary.router)
app.include_router(meals.router)
app.include_router(workouts.router)
app.include_router(body.router)
app.include_router(weekly.router)
