#!/usr/bin/env python3
"""Assign legacy rows with NULL user_id to a specific user UUID.

Usage:
  python scripts/assign_orphan_data.py --user-id <UUID> --dry-run
  python scripts/assign_orphan_data.py --user-id <UUID> --apply

IMPORTANT:
- Backup your database before --apply.
- Local SQLite data is NOT automatically copied to cloud Postgres.
- Never assign orphans to "the first registered user" blindly.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.database import SessionLocal  # noqa: E402
from app.models import DailyEntry, FoodItem, GoalSetting, MealEntry, UserProfile  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Assign orphan records to a user")
    parser.add_argument("--user-id", required=True, help="Target UserProfile / Auth UUID")
    parser.add_argument("--dry-run", action="store_true", help="Only print counts")
    parser.add_argument("--apply", action="store_true", help="Persist the assignment")
    args = parser.parse_args()

    if args.dry_run == args.apply:
        print("请指定 --dry-run 或 --apply 之一。")
        return 2

    db = SessionLocal()
    try:
        user = db.query(UserProfile).filter(UserProfile.id == args.user_id).first()
        if user is None:
            print(f"找不到用户：{args.user_id}")
            return 1

        counts = {
            "meal_entries": db.query(MealEntry).filter(MealEntry.user_id.is_(None)).count(),
            "daily_entries": db.query(DailyEntry).filter(DailyEntry.user_id.is_(None)).count(),
            "goal_settings": db.query(GoalSetting).filter(GoalSetting.user_id.is_(None)).count(),
            "food_items_customish": db.query(FoodItem)
            .filter(FoodItem.owner_user_id.is_(None), FoodItem.source != "seed/manual")
            .count(),
        }
        print("未归属记录数量：")
        for key, value in counts.items():
            print(f"  {key}: {value}")
        print(f"目标用户：{user.email} ({user.id})")

        if args.dry_run:
            print("dry-run 完成，未写入。")
            return 0

        db.query(MealEntry).filter(MealEntry.user_id.is_(None)).update(
            {"user_id": user.id}, synchronize_session=False
        )
        db.query(DailyEntry).filter(DailyEntry.user_id.is_(None)).update(
            {"user_id": user.id}, synchronize_session=False
        )
        db.query(GoalSetting).filter(GoalSetting.user_id.is_(None)).update(
            {"user_id": user.id}, synchronize_session=False
        )
        db.commit()
        print("已写入归属。请重启服务并登录该用户验证。")
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
