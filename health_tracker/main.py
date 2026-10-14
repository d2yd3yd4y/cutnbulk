from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.database import Base, engine, ensure_sqlite_schema
from app.routers import calendar, day, goal, meals, summary


Base.metadata.create_all(bind=engine)
ensure_sqlite_schema()

app = FastAPI(title="cutnbulk")

app.mount("/static", StaticFiles(directory="app/static"), name="static")
app.mount("/uploads", StaticFiles(directory="app/uploads"), name="uploads")


@app.get("/health")
def health_check():
    return {"status": "ok", "app": "cutnbulk"}

app.include_router(calendar.router)
app.include_router(day.router)
app.include_router(goal.router)
app.include_router(summary.router)
app.include_router(meals.router)
