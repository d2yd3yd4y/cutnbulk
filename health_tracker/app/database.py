import os
from pathlib import Path

from sqlalchemy import create_engine, text
from sqlalchemy.orm import DeclarativeBase, sessionmaker

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - python-dotenv is optional at import time.
    load_dotenv = None

if load_dotenv:
    load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent
DEFAULT_SQLITE_URL = f"sqlite:///{BASE_DIR / 'health_tracker.db'}"


def _database_url() -> str:
    url = os.getenv("DATABASE_URL", "").strip()
    if not url:
        return DEFAULT_SQLITE_URL

    # Some hosts expose postgres:// URLs; SQLAlchemy expects postgresql://.
    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql://", 1)
    return url


DATABASE_URL = _database_url()
IS_SQLITE = DATABASE_URL.startswith("sqlite")
connect_args = {"check_same_thread": False} if IS_SQLITE else {}

engine = create_engine(
    DATABASE_URL,
    connect_args=connect_args,
    pool_pre_ping=True,
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
        if meal_columns and "estimate_confidence" not in meal_columns:
            connection.execute(text("ALTER TABLE meal_entries ADD COLUMN estimate_confidence FLOAT"))
        if meal_columns and "estimate_reasoning" not in meal_columns:
            connection.execute(text("ALTER TABLE meal_entries ADD COLUMN estimate_reasoning TEXT"))
        if meal_columns and "estimate_source" not in meal_columns:
            connection.execute(text("ALTER TABLE meal_entries ADD COLUMN estimate_source VARCHAR(40)"))
        if meal_columns and "calorie_range_low" not in meal_columns:
            connection.execute(text("ALTER TABLE meal_entries ADD COLUMN calorie_range_low FLOAT"))
        if meal_columns and "calorie_range_high" not in meal_columns:
            connection.execute(text("ALTER TABLE meal_entries ADD COLUMN calorie_range_high FLOAT"))
        if meal_columns and "uncertainty_factors" not in meal_columns:
            connection.execute(text("ALTER TABLE meal_entries ADD COLUMN uncertainty_factors TEXT"))
