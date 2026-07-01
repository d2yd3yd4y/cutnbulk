from pathlib import Path

from sqlalchemy import create_engine, text
from sqlalchemy.orm import DeclarativeBase, sessionmaker


BASE_DIR = Path(__file__).resolve().parent.parent
DATABASE_URL = f"sqlite:///{BASE_DIR / 'health_tracker.db'}"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def ensure_sqlite_schema():
    """Apply tiny local schema fixes for existing MVP SQLite databases."""
    if engine.dialect.name != "sqlite":
        return

    with engine.begin() as connection:
        meal_columns = {
            row[1] for row in connection.execute(text("PRAGMA table_info(meal_entries)"))
        }
        if meal_columns and "meal_name" not in meal_columns:
            connection.execute(text("ALTER TABLE meal_entries ADD COLUMN meal_name VARCHAR(80)"))
