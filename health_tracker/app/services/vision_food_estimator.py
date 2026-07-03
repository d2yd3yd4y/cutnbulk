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

DEFAULT_MODEL = "gpt-5.4-mini"
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
                    "estimated_grams": {"type": "number"},
                    "calories": {"type": "number"},
                    "protein_g": {"type": "number"},
                    "carbs_g": {"type": "number"},
                    "fat_g": {"type": "number"},
                },
                "required": [
                    "name",
                    "estimated_grams",
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
你是一个谨慎的营养估算助手。请根据食物照片和可选文字描述估算这一顿饭的热量和三大营养素。

用户描述：{description or "未提供"}

要求：
- 特别关注中餐、外卖、食堂餐、盖饭、面食、火锅、麻辣烫、烧烤。
- 不要假装精确，要拆解原材料并给出估算区间。
- 最大误差通常来自米饭重量、油量、酱汁、肉是否带皮、实际份量。
- 如果看不清，请降低 confidence_score，并把原因写入 uncertainty_factors。
- user_friendly_explanation 使用中文，温和具体，提醒用户这是估算，可手动修正。
- 数字使用合理估算，不要输出 null。
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


def _payload_to_result(payload: dict[str, Any]) -> NutritionEstimateResult:
    matches = [
        MatchedFood(
            food_item_id=None,
            name=item["name"],
            matched_text=item["name"],
            estimated_grams=round(float(item["estimated_grams"]), 1),
            calories=round(float(item["calories"]), 1),
            protein_g=round(float(item["protein_g"]), 1),
            carbs_g=round(float(item["carbs_g"]), 1),
            fat_g=round(float(item["fat_g"]), 1),
            confidence=round(float(payload["confidence_score"]), 2),
        )
        for item in payload.get("ingredients", [])
    ]
    return NutritionEstimateResult(
        dish_name=payload["dish_name"],
        calories=round(float(payload["total_calories"]), 1),
        protein_g=round(float(payload["protein_g"]), 1),
        carbs_g=round(float(payload["carbs_g"]), 1),
        fat_g=round(float(payload["fat_g"]), 1),
        confidence=round(float(payload["confidence_score"]), 2),
        confidence_label=payload["confidence_label"],
        reasoning=payload["user_friendly_explanation"],
        matched_foods=matches,
        source="vision_ai",
        calorie_range_low=round(float(payload["calorie_range_low"]), 1),
        calorie_range_high=round(float(payload["calorie_range_high"]), 1),
        uncertainty_factors=payload.get("uncertainty_factors", []),
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
