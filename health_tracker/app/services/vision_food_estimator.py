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
你是饮食记录用的营养估算助手。根据食物照片和可选文字描述，估算这一餐的热量与三大营养素。

用户描述：{description or "未提供"}

目标：
- 尽量识别照片里所有可见食物和配料，哪怕只有一点点。
- 给出接近真实进食份量的估计，不要系统性偏低。
- 不确定也要给数值；用区间和 uncertainty_factors 表达不确定，而不是省略。

识别要求：
1. ingredients 宁多勿漏：主食、蛋白、蔬菜、配菜、酱汁、油脂、炸物、饮品残留、撒料等都尽量单独列出。
2. 酱汁/油脂只要看起来存在（光泽、浇汁、拌匀感），就要单独估克数和热量；名称不确定可写“酱汁/调味油”。
3. 照片中的筷子、叉子、勺子、手、包装文字等可作为尺寸参照；有参照时要用来校准容器和份量。

份量要求：
4. 先判断容器大小和装载程度（小份/普通/大份），再估每种食材克重。
5. 每个食材都必须给出 best_estimate_grams、grams_low、grams_high，以及简短 portion_basis。
6. 看不清时，按该食物在常见成人正餐中的正常份量推断，不要按试吃小份推断。
7. total_calories 应约等于各食材 calories 之和，基于 best_estimate；不要另给更低的“保险总数”。
8. calorie_range_low/high 必须给出合理波动区间；total_calories 可为区间内参考中值。
9. 不确定时宁可略高一点，也不要系统性偏低。

输出要求：
10. 用中文写 user_friendly_explanation 和 uncertainty_factors。
11. 数字全部必填；不要只写“不确定”而不给克数或热量。
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

    # Baseline macros from the model, preferring ingredient sums when higher.
    model_calories = round(float(payload["total_calories"]), 1)
    base_calories = model_calories
    protein_g = round(float(payload["protein_g"]), 1)
    carbs_g = round(float(payload["carbs_g"]), 1)
    fat_g = round(float(payload["fat_g"]), 1)
    if summed_calories > 0 and model_calories < summed_calories * 0.95:
        base_calories = round(summed_calories, 1)
        protein_g = round(summed_protein, 1)
        carbs_g = round(summed_carbs, 1)
        fat_g = round(summed_fat, 1)

    range_low = round(float(payload["calorie_range_low"]), 1)
    range_high = round(float(payload["calorie_range_high"]), 1)
    if range_high < range_low:
        range_low, range_high = range_high, range_low
    if range_high <= 0 and base_calories > 0:
        range_low = round(base_calories * 0.8, 1)
        range_high = round(base_calories * 1.25, 1)
    if range_high < base_calories:
        range_high = round(max(base_calories * 1.15, range_high), 1)
    if range_low <= 0 or range_low > base_calories:
        range_low = round(base_calories * 0.8, 1)

    # Record the high end of the calorie range, not the midpoint.
    calories = range_high if range_high > 0 else base_calories
    if base_calories > 0 and calories != base_calories:
        scale = calories / base_calories
        protein_g = round(protein_g * scale, 1)
        carbs_g = round(carbs_g * scale, 1)
        fat_g = round(fat_g * scale, 1)

    explanation = payload["user_friendly_explanation"]
    if portion_notes:
        explanation = (
            f"{explanation} 已尽量计入可见食材；记录热量取估算区间最大值 "
            f"{calories:g} kcal（区间 {range_low:g}–{range_high:g}）："
            f"{'；'.join(portion_notes[:16])}。"
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
