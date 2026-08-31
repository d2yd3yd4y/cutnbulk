from pathlib import Path

from sqlalchemy.orm import Session


def import_food_items_from_csv(file_path: str | Path, db: Session) -> int:
    """Placeholder for future bulk food database imports.

    Foods can be added manually via /foods/new. This function reserves the import
    seam for USDA, China Food Composition Table, or user-maintained CSV files later.
    """
    raise NotImplementedError("CSV food import UI is not implemented in the MVP.")
