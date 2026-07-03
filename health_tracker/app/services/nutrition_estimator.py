import json
import re
from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.models import FoodItem
from app.services.food_ai_service import estimate_food_nutrition


CHINESE_NUMBERS = {
    "一": 1,
    "二": 2,
    "两": 2,
    "三": 3,
    "四": 4,
    "五": 5,
    "六": 6,
    "七": 7,
    "八": 8,
    "九": 9,
    "十": 10,
    "半": 0.5,
}


@dataclass(frozen=True)
class MatchedFood:
    food_item_id: int | None
    name: str
    matched_text: str
    estimated_grams: float
    calories: float
    protein_g: float
    carbs_g: float
    fat_g: float
    confidence: float


@dataclass(frozen=True)
class NutritionEstimateResult:
    dish_name: str | None
    calories: float
    protein_g: float
    carbs_g: float
    fat_g: float
    confidence: float
    confidence_label: str
    reasoning: str
    matched_foods: list[MatchedFood]
    source: str = "food_database"
    calorie_range_low: float | None = None
    calorie_range_high: float | None = None
    uncertainty_factors: list[str] | None = None


def estimate_meal_nutrition(
    db: Session,
    description: str,
    image_path: str | None = None,
) -> NutritionEstimateResult:
    normalized = normalize_text(description)
    if not normalized:
        return _fallback_estimate(description, image_path)

    food_items = db.query(FoodItem).all()
    matches = _match_food_items(food_items, normalized)
    if not matches:
        return _fallback_estimate(description, image_path)

    calories = round(sum(match.calories for match in matches), 1)
    protein = round(sum(match.protein_g for match in matches), 1)
    carbs = round(sum(match.carbs_g for match in matches), 1)
    fat = round(sum(match.fat_g for match in matches), 1)
    confidence = round(sum(match.confidence for match in matches) / len(matches), 2)
    reasoning_parts = [
        f"{match.name}约{match.estimated_grams:g}g" for match in matches[:6]
    ]
    reasoning = (
        f"匹配到：{'、'.join(reasoning_parts)}，因此估算为 {calories:g} kcal。"
        "中餐和外卖会受油量、酱料和实际份量影响。"
    )

    low, high = _calorie_range(calories, confidence)
    return NutritionEstimateResult(
        dish_name=None,
        calories=calories,
        protein_g=protein,
        carbs_g=carbs,
        fat_g=fat,
        confidence=confidence,
        confidence_label=_confidence_label(confidence),
        reasoning=reasoning,
        matched_foods=matches,
        source="food_database",
        calorie_range_low=low,
        calorie_range_high=high,
        uncertainty_factors=["份量估算", "油量/酱汁", "实际食材差异"],
    )


def normalize_text(value: str) -> str:
    text = value.strip().lower()
    text = re.sub(r"[，。；、,+()（）/]+", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text


def _match_food_items(food_items: list[FoodItem], normalized_text: str) -> list[MatchedFood]:
    candidates: list[tuple[int, int, str, FoodItem]] = []
    for item in food_items:
        aliases = _food_aliases(item)
        for alias in aliases:
            alias_norm = normalize_text(alias)
            if not alias_norm:
                continue
            for match in re.finditer(re.escape(alias_norm), normalized_text):
                candidates.append((match.start(), match.end(), alias_norm, item))

    candidates.sort(key=lambda candidate: (candidate[1] - candidate[0], candidate[0]), reverse=True)
    occupied: list[tuple[int, int]] = []
    selected: list[MatchedFood] = []
    for start, end, alias, item in candidates:
        if any(not (end <= used_start or start >= used_end) for used_start, used_end in occupied):
            continue
        grams, explicit = estimate_portion_grams(normalized_text, start, end, item)
        selected.append(_build_match(item, alias, grams, explicit))
        occupied.append((start, end))

    selected.sort(key=lambda match: normalized_text.find(match.matched_text))
    return selected


def _food_aliases(item: FoodItem) -> list[str]:
    aliases = [item.name, item.normalized_name]
    if item.aliases:
        try:
            aliases.extend(json.loads(item.aliases))
        except json.JSONDecodeError:
            aliases.extend(item.aliases.split(","))
    # Longest first helps avoid matching "米饭" inside "黄焖鸡米饭".
    return sorted({alias for alias in aliases if alias}, key=len, reverse=True)


def estimate_portion_grams(text: str, start: int, end: int, item: FoodItem) -> tuple[float, bool]:
    window_start = max(0, start - 12)
    window_end = min(len(text), end + 12)
    before = text[window_start:start]
    after = text[end:window_end]
    item_text = text[start:end]

    explicit = _parse_explicit_grams(before, after)
    if explicit is not None:
        return explicit, True

    count = _parse_count(before)
    if count is not None and ("蛋" in item.name or "egg" in (item.aliases or "")):
        return round(count * 50, 1), True

    portion = before + item_text + after
    portion_rules = [
        (("半碗",), 0.5),
        (("一碗", "1碗", "碗"), 1.0),
        (("半份",), 0.5),
        (("一份", "1份", "份"), 1.0),
        (("一杯", "1杯", "杯"), 1.0),
        (("一根", "1根", "根"), 1.0),
        (("一个", "1个", "个"), 1.0),
        (("一勺", "1勺", "勺"), 1.0),
        (("一包", "1包", "包"), 1.0),
        (("一瓶", "1瓶", "瓶"), 1.0),
    ]
    for keywords, multiplier in portion_rules:
        if any(keyword in portion for keyword in keywords):
            base = _known_portion_grams(item) or item.serving_grams or 100
            return round(base * multiplier, 1), multiplier != 1.0

    return round(item.serving_grams or 100, 1), False


def _parse_explicit_grams(before: str, after: str) -> float | None:
    match = re.search(r"(\d+(?:\.\d+)?)\s*(?:g|克)\s*$", before)
    if match:
        return float(match.group(1))
    match = re.search(r"^\s*(\d+(?:\.\d+)?)\s*(?:g|克)(?:\s|$)", after)
    if match:
        return float(match.group(1))
    return None


def _parse_count(before: str) -> float | None:
    match = re.search(r"(\d+(?:\.\d+)?)\s*(?:个|颗|只)?$", before)
    if match:
        return float(match.group(1))
    for char, value in CHINESE_NUMBERS.items():
        if before.endswith(char) or before.endswith(f"{char}个") or before.endswith(f"{char}颗"):
            return value
    return None


def _known_portion_grams(item: FoodItem) -> float | None:
    name = item.name
    if "米饭" in name:
        return 200
    if "鸡蛋" in name or name == "茶叶蛋":
        return 50
    if "奶茶" in name:
        return 500
    if "鸡胸肉" in name:
        return 150
    if "牛肉面" in name or "兰州拉面" in name:
        return 600
    if "麻辣烫" in name:
        return 700
    if "火锅" in name:
        return 800
    if "沙拉" in name:
        return 350
    return None


def _build_match(item: FoodItem, matched_text: str, grams: float, explicit: bool) -> MatchedFood:
    factor = grams / 100
    confidence = item.confidence + (0.1 if explicit else 0)
    if item.category in {"中餐菜品", "外卖", "火锅", "烧烤"} and not explicit:
        confidence -= 0.08
    confidence = max(0.25, min(0.95, confidence))
    return MatchedFood(
        food_item_id=item.id,
        name=item.name,
        matched_text=matched_text,
        estimated_grams=round(grams, 1),
        calories=round(item.calories_per_100g * factor, 1),
        protein_g=round(item.protein_per_100g * factor, 1),
        carbs_g=round(item.carbs_per_100g * factor, 1),
        fat_g=round(item.fat_per_100g * factor, 1),
        confidence=round(confidence, 2),
    )


def _fallback_estimate(description: str, image_path: str | None) -> NutritionEstimateResult:
    estimate = estimate_food_nutrition(description, image_path)
    return NutritionEstimateResult(
        dish_name=None,
        calories=estimate.calories,
        protein_g=estimate.protein_g,
        carbs_g=estimate.carbs_g,
        fat_g=estimate.fat_g,
        confidence=0.35,
        confidence_label="low",
        reasoning=f"食物库未匹配到明确条目，使用旧版本地规则估算：{estimate.reasoning}",
        matched_foods=[],
        source="fallback",
        calorie_range_low=round(estimate.calories * 0.65, 1),
        calorie_range_high=round(estimate.calories * 1.35, 1),
        uncertainty_factors=["食物库未匹配", "份量未知", "旧规则估算"],
    )


def _confidence_label(confidence: float) -> str:
    if confidence >= 0.7:
        return "high"
    if confidence >= 0.45:
        return "medium"
    return "low"


def _calorie_range(calories: float, confidence: float) -> tuple[float, float]:
    spread = 0.15 if confidence >= 0.7 else 0.25 if confidence >= 0.45 else 0.35
    return round(calories * (1 - spread), 1), round(calories * (1 + spread), 1)
