from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )


class MealEntry(TimestampMixin, Base):
    __tablename__ = "meal_entries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    entry_date: Mapped[date] = mapped_column(Date, index=True)
    meal_type: Mapped[str] = mapped_column(String(20), index=True)
    meal_name: Mapped[str | None] = mapped_column(String(80), nullable=True)
    description: Mapped[str] = mapped_column(Text)
    image_path: Mapped[str | None] = mapped_column(String(255), nullable=True)
    calories: Mapped[float] = mapped_column(Float, default=0)
    protein_g: Mapped[float] = mapped_column(Float, default=0)
    carbs_g: Mapped[float] = mapped_column(Float, default=0)
    fat_g: Mapped[float] = mapped_column(Float, default=0)
    estimate_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    estimate_reasoning: Mapped[str | None] = mapped_column(Text, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)


class FoodItem(TimestampMixin, Base):
    __tablename__ = "food_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(120), index=True)
    normalized_name: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    aliases: Mapped[str | None] = mapped_column(Text, nullable=True)
    category: Mapped[str | None] = mapped_column(String(80), nullable=True, index=True)
    cuisine: Mapped[str | None] = mapped_column(String(80), nullable=True, index=True)
    serving_desc: Mapped[str | None] = mapped_column(String(80), nullable=True)
    serving_grams: Mapped[float | None] = mapped_column(Float, nullable=True)
    calories_per_100g: Mapped[float] = mapped_column(Float)
    protein_per_100g: Mapped[float] = mapped_column(Float)
    carbs_per_100g: Mapped[float] = mapped_column(Float)
    fat_per_100g: Mapped[float] = mapped_column(Float)
    fiber_per_100g: Mapped[float | None] = mapped_column(Float, nullable=True)
    sodium_per_100g: Mapped[float | None] = mapped_column(Float, nullable=True)
    source: Mapped[str] = mapped_column(String(80), default="seed/manual")
    confidence: Mapped[float] = mapped_column(Float, default=0.7)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)


class MealFoodMatch(Base):
    __tablename__ = "meal_food_matches"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    meal_entry_id: Mapped[int] = mapped_column(ForeignKey("meal_entries.id"), index=True)
    food_item_id: Mapped[int | None] = mapped_column(ForeignKey("food_items.id"), nullable=True)
    matched_text: Mapped[str] = mapped_column(String(120))
    estimated_grams: Mapped[float] = mapped_column(Float)
    calories: Mapped[float] = mapped_column(Float)
    protein_g: Mapped[float] = mapped_column(Float)
    carbs_g: Mapped[float] = mapped_column(Float)
    fat_g: Mapped[float] = mapped_column(Float)
    confidence: Mapped[float] = mapped_column(Float, default=0.7)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class WorkoutEntry(TimestampMixin, Base):
    __tablename__ = "workout_entries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    entry_date: Mapped[date] = mapped_column(Date, index=True)
    exercise: Mapped[str] = mapped_column(String(100), index=True)
    sets: Mapped[int] = mapped_column(Integer, default=0)
    reps: Mapped[int] = mapped_column(Integer, default=0)
    weight_kg: Mapped[float] = mapped_column(Float, default=0)
    rpe: Mapped[int | None] = mapped_column(Integer, nullable=True)
    to_failure: Mapped[bool] = mapped_column(Boolean, default=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    @property
    def volume(self) -> float:
        return self.sets * self.reps * self.weight_kg


class BodyMetric(TimestampMixin, Base):
    __tablename__ = "body_metrics"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    entry_date: Mapped[date] = mapped_column(Date, index=True, unique=True)
    weight_kg: Mapped[float | None] = mapped_column(Float, nullable=True)
    waist_cm: Mapped[float | None] = mapped_column(Float, nullable=True)
    sleep_hours: Mapped[float | None] = mapped_column(Float, nullable=True)
    fatigue_level: Mapped[int | None] = mapped_column(Integer, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)


class DailyEntry(TimestampMixin, Base):
    __tablename__ = "daily_entries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    entry_date: Mapped[date] = mapped_column(Date, index=True, unique=True)
    weight_kg: Mapped[float | None] = mapped_column(Float, nullable=True)
    waist_cm: Mapped[float | None] = mapped_column(Float, nullable=True)
    sleep_hours: Mapped[float | None] = mapped_column(Float, nullable=True)
    fatigue_level: Mapped[int | None] = mapped_column(Integer, nullable=True)
    training_parts: Mapped[str | None] = mapped_column(Text, nullable=True)
    training_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    food_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    image_path: Mapped[str | None] = mapped_column(String(255), nullable=True)
    calories: Mapped[float | None] = mapped_column(Float, nullable=True)
    protein_g: Mapped[float | None] = mapped_column(Float, nullable=True)
    carbs_g: Mapped[float | None] = mapped_column(Float, nullable=True)
    fat_g: Mapped[float | None] = mapped_column(Float, nullable=True)
    daily_note: Mapped[str | None] = mapped_column(Text, nullable=True)


class GoalSetting(TimestampMixin, Base):
    __tablename__ = "goal_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    mode: Mapped[str] = mapped_column(String(20), index=True)
    current_weight_kg: Mapped[float] = mapped_column(Float)
    target_weight_kg: Mapped[float] = mapped_column(Float)
    target_days: Mapped[int] = mapped_column(Integer)
    activity_level: Mapped[str] = mapped_column(String(20), default="moderate")
    maintenance_calories: Mapped[float] = mapped_column(Float)
    recommended_calories: Mapped[float] = mapped_column(Float)
    daily_energy_delta: Mapped[float] = mapped_column(Float)
    weekly_weight_change: Mapped[float] = mapped_column(Float)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
