import base64
import io
import json
import os
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from openai import OpenAI
from PIL import Image
from sqlalchemy.orm import Session

from app.database import BASE_DIR
from app.services.nutrition_estimator import (
    MatchedFood,
    NutritionEstimateResult,
    estimate_meal_nutrition,
)


load_dotenv()

DEFAULT_MODEL = "gpt-4.1-mini"
MAX_IMAGE_SIZE = 1024
JPEG_QUALITY = 78

# Typical adult meal defaults used when the photo is ambiguous.
DEFAULT_PORTION_HINTS = """
常见成人份量参考（看不清时用这些作为 best_estimate，而不是省略）：
- 米饭（一碗/外卖盒一半）：180–220g 熟重，默认 200g
- 三文鱼/鱼排一块：120–180g，默认 150g
- 鸡胸/瘦肉一块：120–180g，默认 150g
- 红肉/五花等：100–160g，默认 130g
- 炒菜油脂：8–20g，默认 12g
- 酱汁/浇汁：20–60g，默认 35g
- 蔬菜配菜：80–150g，默认 100g
- 普通成人餐盘主食+蛋白套餐总热量：通常 550–900 kcal，不要系统性偏低
"""


FOOD_ESTIMATE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "dish_name": {"type": "string"},
        "total_calories": {"type": "number"},
        "protein_g": {"type": "number"},
        "carbs_g": {"type": "number"},
        "fat_g": {"type": "number"},
        "confidence_score": {"type": "number", "minimum": 0, "maximum": 1},
        "confidence_label": {"type": "string", "enum": ["high", "medium", "low"]},
        "ingredients": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "name": {"type": "string"},
                    "best_estimate_grams": {"type": "number"},
                    "grams_low": {"type": "number"},
                    "grams_high": {"type": "number"},
                    "portion_basis": {"type": "string"},
                    "calories": {"type": "number"},
                    "protein_g": {"type": "number"},
                    "carbs_g": {"type": "number"},
                    "fat_g": {"type": "number"},
                },
                "required": [
                    "name",
                    "best_estimate_grams",
                    "grams_low",
                    "grams_high",
                    "portion_basis",
                    "calories",
                    "protein_g",
                    "carbs_g",
                    "fat_g",
                ],
            },
        },
        "uncertainty_factors": {"type": "array", "items": {"type": "string"}},
        "calorie_range_low": {"type": "number"},
        "calorie_range_high": {"type": "number"},
        "user_friendly_explanation": {"type": "string"},
    },
    "required": [
        "dish_name",
        "total_calories",
        "protein_g",
        "carbs_g",
        "fat_g",
        "confidence_score",
        "confidence_label",
        "ingredients",
        "uncertainty_factors",
        "calorie_range_low",
        "calorie_range_high",
        "user_friendly_explanation",
    ],
}


def estimate_food_from_image(
    db: Session,
    image_path: str | None,
    description: str = "",
) -> NutritionEstimateResult:
    """Estimate meal nutrition from a photo, with local fallback.

    Missing API key or API errors never break meal saving; local food database
    estimation remains the fallback path.
    """
    if not image_path:
        return estimate_meal_nutrition(db, description)

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        fallback = estimate_meal_nutrition(db, description, image_path)
        return _with_fallback_reason(fallback, "未配置 OPENAI_API_KEY，已使用本地食物库估算。")

    try:
        image_data_url = _image_to_data_url(image_path)
        client = OpenAI(api_key=api_key)
        model = os.getenv("OPENAI_FOOD_MODEL", DEFAULT_MODEL)
        response = client.responses.create(
            model=model,
            input=[
                {
                    "role": "user",
                    "content": [
                        {"type": "input_text", "text": _build_prompt(description)},
                        {"type": "input_image", "image_url": image_data_url},
                    ],
                }
            ],
            text={
                "format": {
                    "type": "json_schema",
                    "name": "food_nutrition_estimate",
                    "schema": FOOD_ESTIMATE_SCHEMA,
                    "strict": True,
                }
            },
        )
        payload = json.loads(response.output_text)
        return _payload_to_result(payload)
    except Exception as exc:  # Keep saving resilient for local-first MVP.
        fallback = estimate_meal_nutrition(db, description, image_path)
        return _with_fallback_reason(
            fallback,
            f"OpenAI 视觉估算失败，已使用本地食物库估算。错误：{exc}",
        )


def _build_prompt(description: str) -> str:
    return f"""
你是面向真实饮食记录场景的营养估算助手。请根据食物照片和可选文字描述，估算这一顿饭的热量和三大营养素。

用户描述：{description or "未提供"}

{DEFAULT_PORTION_HINTS}

核心规则（必须遵守）：
1. 必须做视觉份量推断：根据餐盘/碗/外卖盒、食物厚度、占盘比例、相对筷子或容器大小判断克重。
2. 每个可见食材都必须给出 best_estimate_grams，以及 grams_low / grams_high。禁止只写“不确定”而不给数值。
3. 对米饭、三文鱼、肉类、油脂、酱汁这些高热量影响项：即使模糊，也必须给出克重区间和 best_estimate；可用常见成人份量补全。
4. total_calories、protein_g、carbs_g、fat_g 必须基于各食材的 best_estimate_grams 汇总，不要取偏低保守值当主结果。
5. calorie_range_low / calorie_range_high 表达不确定性；主结果（total_calories）应落在区间中部附近，不要系统性偏低。
6. 看不清时按“普通成人一餐”推断，而不是按很小试吃份量推断。
7. uncertainty_factors 用中文说明哪里不确定（如油量、米饭厚度、是否含酱），但不确定性不能阻止你给出数值。
8. portion_basis 简短说明该克重依据（如“约半盒米饭，对照外卖盒估 200g”）。
9. user_friendly_explanation 用中文说明：按视觉估了哪些份量、哪里不确定、用户可手动修正。
10. 数字全部必填，不要 null；ingredients 至少包含照片中主要可见食物。
""".strip()


def _image_to_data_url(image_path: str) -> str:
    path = _resolve_image_path(image_path)
    with Image.open(path) as image:
        image = image.convert("RGB")
        image.thumbnail((MAX_IMAGE_SIZE, MAX_IMAGE_SIZE))
        buffer = io.BytesIO()
        image.save(buffer, format="JPEG", quality=JPEG_QUALITY, optimize=True)
    encoded = base64.b64encode(buffer.getvalue()).decode("ascii")
    return f"data:image/jpeg;base64,{encoded}"


def _resolve_image_path(image_path: str) -> Path:
    if image_path.startswith("/uploads/"):
        return BASE_DIR / "app" / "uploads" / image_path.replace("/uploads/", "", 1)
    path = Path(image_path)
    if not path.is_absolute():
        path = BASE_DIR / path
    return path


def _ingredient_grams(item: dict[str, Any]) -> float:
    best = item.get("best_estimate_grams")
    if best is not None:
        return max(0.0, float(best))
    estimated = item.get("estimated_grams")
    if estimated is not None:
        return max(0.0, float(estimated))
    low = float(item.get("grams_low") or 0)
    high = float(item.get("grams_high") or 0)
    if low or high:
        return max(0.0, (low + high) / 2)
    return 0.0


def _payload_to_result(payload: dict[str, Any]) -> NutritionEstimateResult:
    ingredients = payload.get("ingredients") or []
    matches: list[MatchedFood] = []
    portion_notes: list[str] = []
    summed_calories = 0.0
    summed_protein = 0.0
    summed_carbs = 0.0
    summed_fat = 0.0

    for item in ingredients:
        grams = round(_ingredient_grams(item), 1)
        calories = round(float(item.get("calories") or 0), 1)
        protein = round(float(item.get("protein_g") or 0), 1)
        carbs = round(float(item.get("carbs_g") or 0), 1)
        fat = round(float(item.get("fat_g") or 0), 1)
        summed_calories += calories
        summed_protein += protein
        summed_carbs += carbs
        summed_fat += fat

        grams_low = item.get("grams_low")
        grams_high = item.get("grams_high")
        if grams_low is not None and grams_high is not None:
            portion_notes.append(
                f"{item['name']}约{grams:g}g（区间{float(grams_low):g}–{float(grams_high):g}g）"
            )
        else:
            portion_notes.append(f"{item['name']}约{grams:g}g")

        matches.append(
            MatchedFood(
                food_item_id=None,
                name=item["name"],
                matched_text=item["name"],
                estimated_grams=grams,
                calories=calories,
                protein_g=protein,
                carbs_g=carbs,
                fat_g=fat,
                confidence=round(float(payload["confidence_score"]), 2),
            )
        )

    # Prefer ingredient-summed macros when the model under-reports the headline total.
    model_calories = round(float(payload["total_calories"]), 1)
    calories = model_calories
    protein_g = round(float(payload["protein_g"]), 1)
    carbs_g = round(float(payload["carbs_g"]), 1)
    fat_g = round(float(payload["fat_g"]), 1)
    if summed_calories > 0 and model_calories < summed_calories * 0.85:
        calories = round(summed_calories, 1)
        protein_g = round(summed_protein, 1)
        carbs_g = round(summed_carbs, 1)
        fat_g = round(summed_fat, 1)

    range_low = round(float(payload["calorie_range_low"]), 1)
    range_high = round(float(payload["calorie_range_high"]), 1)
    if range_high < calories:
        range_high = round(calories * 1.15, 1)
    if range_low > calories:
        range_low = round(calories * 0.85, 1)
    # Keep the reported point estimate near the middle of a usable logging range.
    if calories - range_low > range_high - calories and range_high > calories:
        range_low = round(max(calories * 0.8, calories - (range_high - calories)), 1)

    explanation = payload["user_friendly_explanation"]
    if portion_notes:
        explanation = (
            f"{explanation} 份量取 best estimate：{'；'.join(portion_notes[:8])}。"
        )

    uncertainty = list(payload.get("uncertainty_factors") or [])
    if not any("份量" in factor or "克" in factor for factor in uncertainty):
        uncertainty.append("份量为视觉估算，实际克重可能有偏差，可手动修正。")

    return NutritionEstimateResult(
        dish_name=payload["dish_name"],
        calories=calories,
        protein_g=protein_g,
        carbs_g=carbs_g,
        fat_g=fat_g,
        confidence=round(float(payload["confidence_score"]), 2),
        confidence_label=payload["confidence_label"],
        reasoning=explanation,
        matched_foods=matches,
        source="vision_ai",
        calorie_range_low=range_low,
        calorie_range_high=range_high,
        uncertainty_factors=uncertainty,
    )


def _with_fallback_reason(
    result: NutritionEstimateResult,
    reason: str,
) -> NutritionEstimateResult:
    return NutritionEstimateResult(
        dish_name=result.dish_name,
        calories=result.calories,
        protein_g=result.protein_g,
        carbs_g=result.carbs_g,
        fat_g=result.fat_g,
        confidence=result.confidence,
        confidence_label=result.confidence_label,
        reasoning=f"{reason} {result.reasoning}",
        matched_foods=result.matched_foods,
        source="fallback",
        calorie_range_low=result.calorie_range_low,
        calorie_range_high=result.calorie_range_high,
        uncertainty_factors=result.uncertainty_factors,
    )
