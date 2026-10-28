from __future__ import annotations

from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect, text


def test_alembic_upgrade_empty_sqlite(tmp_path: Path, monkeypatch):
    db_path = tmp_path / "migrate.db"
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("AUTH_MODE", "local")
    monkeypatch.setenv("SECRET_KEY", "test-secret")
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path}")
    monkeypatch.setenv("COOKIE_SECURE", "false")

    from app.config import reset_settings_cache

    reset_settings_cache()

    cfg = Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"))
    cfg.set_main_option("script_location", str(Path(__file__).resolve().parents[1] / "alembic"))
    cfg.set_main_option("sqlalchemy.url", f"sqlite:///{db_path}")
    command.upgrade(cfg, "head")

    engine = create_engine(f"sqlite:///{db_path}")
    tables = set(inspect(engine).get_table_names())
    assert "user_profiles" in tables
    assert "auth_sessions" in tables
    assert "meal_entries" in tables
    assert "daily_entries" in tables
    cols = {c["name"] for c in inspect(engine).get_columns("meal_entries")}
    assert "user_id" in cols


def test_alembic_upgrade_existing_sqlite(tmp_path: Path, monkeypatch):
    db_path = tmp_path / "legacy.db"
    engine = create_engine(f"sqlite:///{db_path}")
    with engine.begin() as conn:
        conn.execute(
            text(
                """
                CREATE TABLE meal_entries (
                    id INTEGER PRIMARY KEY,
                    entry_date DATE NOT NULL,
                    meal_type VARCHAR(20) NOT NULL,
                    description TEXT NOT NULL,
                    image_path VARCHAR(255),
                    calories FLOAT DEFAULT 0,
                    protein_g FLOAT DEFAULT 0,
                    carbs_g FLOAT DEFAULT 0,
                    fat_g FLOAT DEFAULT 0,
                    created_at DATETIME,
                    updated_at DATETIME
                )
                """
            )
        )
        conn.execute(
            text(
                """
                CREATE TABLE daily_entries (
                    id INTEGER PRIMARY KEY,
                    entry_date DATE NOT NULL UNIQUE,
                    weight_kg FLOAT,
                    created_at DATETIME,
                    updated_at DATETIME
                )
                """
            )
        )
        conn.execute(
            text(
                """
                CREATE TABLE goal_settings (
                    id INTEGER PRIMARY KEY,
                    mode VARCHAR(20) NOT NULL,
                    current_weight_kg FLOAT NOT NULL,
                    target_weight_kg FLOAT NOT NULL,
                    target_days INTEGER NOT NULL,
                    activity_level VARCHAR(20) DEFAULT 'moderate',
                    maintenance_calories FLOAT NOT NULL,
                    recommended_calories FLOAT NOT NULL,
                    daily_energy_delta FLOAT NOT NULL,
                    weekly_weight_change FLOAT NOT NULL,
                    is_active BOOLEAN DEFAULT 1,
                    created_at DATETIME,
                    updated_at DATETIME
                )
                """
            )
        )

    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("AUTH_MODE", "local")
    monkeypatch.setenv("SECRET_KEY", "test-secret")
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path}")
    from app.config import reset_settings_cache

    reset_settings_cache()
    cfg = Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"))
    cfg.set_main_option("script_location", str(Path(__file__).resolve().parents[1] / "alembic"))
    cfg.set_main_option("sqlalchemy.url", f"sqlite:///{db_path}")
    command.upgrade(cfg, "head")

    cols = {c["name"] for c in inspect(engine).get_columns("meal_entries")}
    assert "user_id" in cols
    assert "user_profiles" in inspect(engine).get_table_names()
