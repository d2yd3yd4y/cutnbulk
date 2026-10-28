#!/usr/bin/env python3
"""Upload legacy local meal photos to Supabase Storage and rewrite image_path keys.

Usage:
  python scripts/migrate_local_images.py --dry-run
  python scripts/migrate_local_images.py --apply

Requires cloud storage env vars. Only migrates rows that already have user_id.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.config import get_settings  # noqa: E402
from app.database import SessionLocal  # noqa: E402
from app.models import MealEntry  # noqa: E402
from app.services.storage import storage_service  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    if args.dry_run == args.apply:
        print("请指定 --dry-run 或 --apply 之一。")
        return 2

    settings = get_settings()
    if not settings.uses_cloud_storage:
        print("未配置 Supabase Storage，无法迁移。")
        return 1

    db = SessionLocal()
    try:
        meals = (
            db.query(MealEntry)
            .filter(MealEntry.user_id.isnot(None), MealEntry.image_path.isnot(None))
            .all()
        )
        candidates = [
            meal
            for meal in meals
            if meal.image_path.startswith("/uploads/") or not meal.image_path.startswith("meals/")
        ]
        print(f"待迁移图片记录：{len(candidates)}")
        if args.dry_run:
            for meal in candidates[:20]:
                print(f"  meal#{meal.id} user={meal.user_id} path={meal.image_path}")
            return 0

        for meal in candidates:
            local = storage_service.open_local_file(meal.image_path)
            if local is None:
                print(f"跳过 meal#{meal.id}：本地文件不存在")
                continue
            new_key = storage_service.save_meal_image(meal.user_id, local.read_bytes(), local.name)
            old = meal.image_path
            meal.image_path = new_key
            db.commit()
            print(f"meal#{meal.id}: {old} -> {new_key}")
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
