import re


def normalize_food_name(value: str) -> str:
    return re.sub(r"\s+", "", value.strip().lower())
