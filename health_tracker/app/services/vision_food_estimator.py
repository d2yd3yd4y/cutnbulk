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

核心目标：
- 完整识别所有可见食物/配料（包括少量撒料、酱汁、油脂、炸物）。
- 按真实成人正餐份量估算，严禁系统性低估。
- 视觉模型常把主食和蛋白估小；你要主动纠正这种偏差。
- 不确定也要给数值，用 grams_low/grams_high 和 uncertainty_factors 表达不确定。

识别要求：
1. ingredients 宁多勿漏。
2. 酱汁/油脂只要看起来存在，就必须单独成行并给克数热量。
3. 若照片有筷子、叉子、勺子、手、包装文字，用作尺寸参照，并写进 portion_basis。

份量要求（很重要）：
4. 先判断容器是小/中/大。大碗、装得很满、食物堆得高时，主食和蛋白必须明显上调。
5. best_estimate_grams 应接近你认为最可能的真实进食量；不要给“保险偏小”的克数。
6. grams_high 必须覆盖“这顿实际可能偏大”的情况，不能只比 best_estimate 大一点点。
7. 每个食材的 calories / protein_g / carbs_g / fat_g 必须与 best_estimate_grams 对应。
8. total_calories ≈ 各食材 calories 之和。
9. calorie_range_high 必须按更大份量情景估算（接近各食材偏高克重对应热量之和），不能只比 total_calories 高几十卡就封顶。
10. 不确定时宁可略高，不要偏低。

输出要求：
11. 中文写 user_friendly_explanation 和 uncertainty_factors。
12. 数字全部必填。
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


def _scale_macros(
    calories: float,
    protein_g: float,
    carbs_g: float,
    fat_g: float,
    from_grams: float,
    to_grams: float,
) -> tuple[float, float, float, float]:
    if from_grams <= 0 or to_grams <= 0:
        return calories, protein_g, carbs_g, fat_g
    scale = to_grams / from_grams
    return (
        round(calories * scale, 1),
        round(protein_g * scale, 1),
        round(carbs_g * scale, 1),
        round(fat_g * scale, 1),
    )


def _payload_to_result(payload: dict[str, Any]) -> NutritionEstimateResult:
    ingredients = payload.get("ingredients") or []
    matches: list[MatchedFood] = []
    portion_notes: list[str] = []
    high_calories = 0.0
    high_protein = 0.0
    high_carbs = 0.0
    high_fat = 0.0
    low_calories = 0.0

    for item in ingredients:
        best_grams = round(_ingredient_grams(item), 1)
        grams_low = float(item.get("grams_low") or best_grams)
        grams_high = float(item.get("grams_high") or best_grams)
        if grams_high < best_grams:
            grams_high = best_grams
        if grams_low <= 0:
            grams_low = best_grams
        # Models often give a too-narrow high bound; widen slightly for logging.
        if best_grams > 0 and grams_high < best_grams * 1.25:
            grams_high = round(best_grams * 1.35, 1)

        base_cal = float(item.get("calories") or 0)
        base_protein = float(item.get("protein_g") or 0)
        base_carbs = float(item.get("carbs_g") or 0)
        base_fat = float(item.get("fat_g") or 0)

        # Record using the high-end portion so UI grams match max-calorie logging.
        calories, protein, carbs, fat = _scale_macros(
            base_cal, base_protein, base_carbs, base_fat, best_grams, grams_high
        )
        low_cal, _, _, _ = _scale_macros(
            base_cal, base_protein, base_carbs, base_fat, best_grams, grams_low
        )

        high_calories += calories
        high_protein += protein
        high_carbs += carbs
        high_fat += fat
        low_calories += low_cal

        portion_notes.append(
            f"{item['name']}按偏高份量约{grams_high:g}g（模型区间{grams_low:g}–{grams_high:g}g）"
        )
        matches.append(
            MatchedFood(
                food_item_id=None,
                name=item["name"],
                matched_text=item["name"],
                estimated_grams=round(grams_high, 1),
                calories=calories,
                protein_g=protein,
                carbs_g=carbs,
                fat_g=fat,
                confidence=round(float(payload["confidence_score"]), 2),
            )
        )

    model_high = round(float(payload.get("calorie_range_high") or 0), 1)
    model_low = round(float(payload.get("calorie_range_low") or 0), 1)
    range_high = round(max(high_calories, model_high), 1)
    range_low = round(min(low_calories, model_low) if model_low > 0 else low_calories, 1)
    if range_high < range_low:
        range_low, range_high = range_high, range_low
    if range_high <= 0:
        range_high = round(float(payload.get("total_calories") or 0), 1)
        range_low = round(range_high * 0.8, 1)

    calories = range_high
    protein_g = round(high_protein, 1)
    carbs_g = round(high_carbs, 1)
    fat_g = round(high_fat, 1)

    explanation = payload["user_friendly_explanation"]
    if portion_notes:
        explanation = (
            f"{explanation} 记录时按各食材偏高克重汇总："
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
