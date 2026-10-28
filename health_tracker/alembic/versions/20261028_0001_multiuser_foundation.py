"""multiuser foundation

Revision ID: 20261028_0001
Revises:
Create Date: 2026-10-28

Creates multi-user schema for empty databases and upgrades existing
SQLite/Postgres tables created by the earlier create_all MVP.
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "20261028_0001"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_table(name: str) -> bool:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return name in inspector.get_table_names()


def _columns(table: str) -> set[str]:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if table not in inspector.get_table_names():
        return set()
    return {col["name"] for col in inspector.get_columns(table)}


def upgrade() -> None:
    if not _has_table("user_profiles"):
        op.create_table(
            "user_profiles",
            sa.Column("id", sa.String(length=36), primary_key=True),
            sa.Column("email", sa.String(length=255), nullable=False),
            sa.Column("display_name", sa.String(length=120), nullable=True),
            sa.Column("timezone", sa.String(length=64), nullable=False, server_default="Asia/Shanghai"),
            sa.Column("onboarding_completed", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("password_hash", sa.String(length=255), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
        )
        op.create_index("ix_user_profiles_email", "user_profiles", ["email"], unique=True)
        op.create_index("ix_user_profiles_onboarding_completed", "user_profiles", ["onboarding_completed"])

    if not _has_table("auth_sessions"):
        op.create_table(
            "auth_sessions",
            sa.Column("id", sa.String(length=64), primary_key=True),
            sa.Column("user_id", sa.String(length=36), sa.ForeignKey("user_profiles.id"), nullable=False),
            sa.Column("access_token", sa.Text(), nullable=True),
            sa.Column("refresh_token", sa.Text(), nullable=True),
            sa.Column("expires_at", sa.DateTime(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("last_seen_at", sa.DateTime(), nullable=False),
            sa.Column("revoked_at", sa.DateTime(), nullable=True),
        )
        op.create_index("ix_auth_sessions_user_id", "auth_sessions", ["user_id"])

    if not _has_table("meal_entries"):
        op.create_table(
            "meal_entries",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("user_id", sa.String(length=36), sa.ForeignKey("user_profiles.id"), nullable=True),
            sa.Column("entry_date", sa.Date(), nullable=False),
            sa.Column("meal_type", sa.String(length=20), nullable=False),
            sa.Column("meal_name", sa.String(length=80), nullable=True),
            sa.Column("description", sa.Text(), nullable=False),
            sa.Column("image_path", sa.String(length=512), nullable=True),
            sa.Column("calories", sa.Float(), nullable=False, server_default="0"),
            sa.Column("protein_g", sa.Float(), nullable=False, server_default="0"),
            sa.Column("carbs_g", sa.Float(), nullable=False, server_default="0"),
            sa.Column("fat_g", sa.Float(), nullable=False, server_default="0"),
            sa.Column("estimate_confidence", sa.Float(), nullable=True),
            sa.Column("estimate_reasoning", sa.Text(), nullable=True),
            sa.Column("estimate_source", sa.String(length=40), nullable=True),
            sa.Column("calorie_range_low", sa.Float(), nullable=True),
            sa.Column("calorie_range_high", sa.Float(), nullable=True),
            sa.Column("uncertainty_factors", sa.Text(), nullable=True),
            sa.Column("notes", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
        )
        op.create_index("ix_meal_entries_user_id", "meal_entries", ["user_id"])
        op.create_index("ix_meal_entries_entry_date", "meal_entries", ["entry_date"])
        op.create_index("ix_meal_entries_meal_type", "meal_entries", ["meal_type"])
    else:
        cols = _columns("meal_entries")
        with op.batch_alter_table("meal_entries") as batch:
            if "user_id" not in cols:
                batch.add_column(sa.Column("user_id", sa.String(length=36), nullable=True))
            if "image_path" in cols:
                batch.alter_column("image_path", type_=sa.String(length=512), existing_type=sa.String(length=255))

    if not _has_table("food_items"):
        op.create_table(
            "food_items",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("owner_user_id", sa.String(length=36), sa.ForeignKey("user_profiles.id"), nullable=True),
            sa.Column("name", sa.String(length=120), nullable=False),
            sa.Column("normalized_name", sa.String(length=120), nullable=False),
            sa.Column("aliases", sa.Text(), nullable=True),
            sa.Column("category", sa.String(length=80), nullable=True),
            sa.Column("cuisine", sa.String(length=80), nullable=True),
            sa.Column("serving_desc", sa.String(length=80), nullable=True),
            sa.Column("serving_grams", sa.Float(), nullable=True),
            sa.Column("calories_per_100g", sa.Float(), nullable=False),
            sa.Column("protein_per_100g", sa.Float(), nullable=False),
            sa.Column("carbs_per_100g", sa.Float(), nullable=False),
            sa.Column("fat_per_100g", sa.Float(), nullable=False),
            sa.Column("fiber_per_100g", sa.Float(), nullable=True),
            sa.Column("sodium_per_100g", sa.Float(), nullable=True),
            sa.Column("source", sa.String(length=80), nullable=False, server_default="seed/manual"),
            sa.Column("confidence", sa.Float(), nullable=False, server_default="0.7"),
            sa.Column("notes", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.UniqueConstraint("owner_user_id", "normalized_name", name="uq_food_owner_normalized"),
        )
    else:
        cols = _columns("food_items")
        with op.batch_alter_table("food_items") as batch:
            if "owner_user_id" not in cols:
                batch.add_column(sa.Column("owner_user_id", sa.String(length=36), nullable=True))
            # Drop global unique on normalized_name if present; recreate composite later via app usage.
            try:
                batch.drop_constraint("normalized_name", type_="unique")
            except Exception:
                pass
            try:
                batch.create_unique_constraint(
                    "uq_food_owner_normalized",
                    ["owner_user_id", "normalized_name"],
                )
            except Exception:
                pass

    if not _has_table("meal_food_matches"):
        op.create_table(
            "meal_food_matches",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("meal_entry_id", sa.Integer(), sa.ForeignKey("meal_entries.id"), nullable=False),
            sa.Column("food_item_id", sa.Integer(), sa.ForeignKey("food_items.id"), nullable=True),
            sa.Column("matched_text", sa.String(length=120), nullable=False),
            sa.Column("estimated_grams", sa.Float(), nullable=False),
            sa.Column("calories", sa.Float(), nullable=False),
            sa.Column("protein_g", sa.Float(), nullable=False),
            sa.Column("carbs_g", sa.Float(), nullable=False),
            sa.Column("fat_g", sa.Float(), nullable=False),
            sa.Column("confidence", sa.Float(), nullable=False, server_default="0.7"),
            sa.Column("created_at", sa.DateTime(), nullable=False),
        )

    if not _has_table("daily_entries"):
        op.create_table(
            "daily_entries",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("user_id", sa.String(length=36), sa.ForeignKey("user_profiles.id"), nullable=True),
            sa.Column("entry_date", sa.Date(), nullable=False),
            sa.Column("weight_kg", sa.Float(), nullable=True),
            sa.Column("waist_cm", sa.Float(), nullable=True),
            sa.Column("sleep_hours", sa.Float(), nullable=True),
            sa.Column("fatigue_level", sa.Integer(), nullable=True),
            sa.Column("training_parts", sa.Text(), nullable=True),
            sa.Column("training_notes", sa.Text(), nullable=True),
            sa.Column("food_description", sa.Text(), nullable=True),
            sa.Column("image_path", sa.String(length=512), nullable=True),
            sa.Column("calories", sa.Float(), nullable=True),
            sa.Column("protein_g", sa.Float(), nullable=True),
            sa.Column("carbs_g", sa.Float(), nullable=True),
            sa.Column("fat_g", sa.Float(), nullable=True),
            sa.Column("daily_note", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.UniqueConstraint("user_id", "entry_date", name="uq_daily_user_date"),
        )
        op.create_index("ix_daily_entries_user_id", "daily_entries", ["user_id"])
        op.create_index("ix_daily_entries_entry_date", "daily_entries", ["entry_date"])
    else:
        cols = _columns("daily_entries")
        dialect = op.get_bind().dialect.name
        if "user_id" not in cols:
            if dialect == "sqlite":
                # SQLite UNIQUE(entry_date) is often inline; rebuild table.
                op.execute("ALTER TABLE daily_entries RENAME TO daily_entries_old")
                op.create_table(
                    "daily_entries",
                    sa.Column("id", sa.Integer(), primary_key=True),
                    sa.Column("user_id", sa.String(length=36), nullable=True),
                    sa.Column("entry_date", sa.Date(), nullable=False),
                    sa.Column("weight_kg", sa.Float(), nullable=True),
                    sa.Column("waist_cm", sa.Float(), nullable=True),
                    sa.Column("sleep_hours", sa.Float(), nullable=True),
                    sa.Column("fatigue_level", sa.Integer(), nullable=True),
                    sa.Column("training_parts", sa.Text(), nullable=True),
                    sa.Column("training_notes", sa.Text(), nullable=True),
                    sa.Column("food_description", sa.Text(), nullable=True),
                    sa.Column("image_path", sa.String(length=512), nullable=True),
                    sa.Column("calories", sa.Float(), nullable=True),
                    sa.Column("protein_g", sa.Float(), nullable=True),
                    sa.Column("carbs_g", sa.Float(), nullable=True),
                    sa.Column("fat_g", sa.Float(), nullable=True),
                    sa.Column("daily_note", sa.Text(), nullable=True),
                    sa.Column("created_at", sa.DateTime(), nullable=True),
                    sa.Column("updated_at", sa.DateTime(), nullable=True),
                    sa.UniqueConstraint("user_id", "entry_date", name="uq_daily_user_date"),
                )
                old_cols = _columns("daily_entries_old")
                copy_cols = [
                    c
                    for c in [
                        "id",
                        "entry_date",
                        "weight_kg",
                        "waist_cm",
                        "sleep_hours",
                        "fatigue_level",
                        "training_parts",
                        "training_notes",
                        "food_description",
                        "image_path",
                        "calories",
                        "protein_g",
                        "carbs_g",
                        "fat_g",
                        "daily_note",
                        "created_at",
                        "updated_at",
                    ]
                    if c in old_cols
                ]
                cols_csv = ", ".join(copy_cols)
                op.execute(
                    f"INSERT INTO daily_entries ({cols_csv}) SELECT {cols_csv} FROM daily_entries_old"
                )
                op.drop_table("daily_entries_old")
                op.create_index("ix_daily_entries_user_id", "daily_entries", ["user_id"])
                op.create_index("ix_daily_entries_entry_date", "daily_entries", ["entry_date"])
            else:
                with op.batch_alter_table("daily_entries") as batch:
                    batch.add_column(sa.Column("user_id", sa.String(length=36), nullable=True))
                    batch.create_unique_constraint("uq_daily_user_date", ["user_id", "entry_date"])

    if not _has_table("goal_settings"):
        op.create_table(
            "goal_settings",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("user_id", sa.String(length=36), sa.ForeignKey("user_profiles.id"), nullable=True),
            sa.Column("mode", sa.String(length=20), nullable=False),
            sa.Column("current_weight_kg", sa.Float(), nullable=False),
            sa.Column("target_weight_kg", sa.Float(), nullable=False),
            sa.Column("target_days", sa.Integer(), nullable=False),
            sa.Column("activity_level", sa.String(length=20), nullable=False, server_default="moderate"),
            sa.Column("maintenance_calories", sa.Float(), nullable=False),
            sa.Column("recommended_calories", sa.Float(), nullable=False),
            sa.Column("daily_energy_delta", sa.Float(), nullable=False),
            sa.Column("weekly_weight_change", sa.Float(), nullable=False),
            sa.Column("note", sa.Text(), nullable=True),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
        )
        op.create_index("ix_goal_settings_user_id", "goal_settings", ["user_id"])
        op.create_index("ix_goal_settings_mode", "goal_settings", ["mode"])
        op.create_index("ix_goal_settings_is_active", "goal_settings", ["is_active"])
    else:
        cols = _columns("goal_settings")
        with op.batch_alter_table("goal_settings") as batch:
            if "user_id" not in cols:
                batch.add_column(sa.Column("user_id", sa.String(length=36), nullable=True))


def downgrade() -> None:
    # Keep downgrade conservative: do not drop user data tables automatically.
    pass
