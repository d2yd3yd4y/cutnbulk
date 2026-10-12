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

# Typical adult / large restaurant bowl defaults when the photo is ambiguous.
DEFAULT_PORTION_HINTS = """
常见成人/大碗餐厅份量参考（宁可接近真实一餐，严禁系统性偏低）：
- 米饭/寿司米（大碗底层铺满）：250–350g 熟重，默认 280g（约 360–450 kcal）
- 三文鱼/刺身蛋白：160–220g，默认 180g（约 300–400 kcal）
- 鸡胸/瘦肉：160–220g，默认 180g
- 牛油果：70–120g，默认 90g
- 蛋黄酱/spicy mayo/芝麻酱：25–50g，默认 35g（必须单独成行）
- 浇汁/酱油基酱/沙拉汁：30–60g，默认 40g（必须单独成行）
- 食用油/香油：10–25g，默认 15g（有油光时必须估算）
- 炸物（馄饨皮/脆片等）：30–70g，默认 45g
- 海草、毛豆、黄瓜、萝卜丝、葱花、芝麻、蟹棒等：一点点也要单独估算
- 大号 poke bowl / 生鱼片盖饭（碗口很大、装得很满）：常落在 950–1200 kcal；不要估成 550–750
- 若碗明显大于普通家用碗，米饭和蛋白都应往上取，而不是取小份默认值

尺寸参照（照片里若有餐具，必须用来校准份量）：
- 筷子：常见约 22–24cm，可用来估碗直径、鱼片长度、米饭面积
- 叉子/勺子：常见餐叉全长约 18–20cm，勺头宽度可估酱汁和配菜体积
- 若碗直径明显大于一双筷子长度的大部分，按“大碗/超大碗”处理，提高米饭与总热量
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
你是面向真实饮食记录场景的营养估算助手。用户常用很大的碗吃饭，也可能把筷子/叉子/勺子拍进照片当尺寸参照。
你的目标是：完整识别食物，并给出接近真实大份餐厅餐的热量；严禁保守低估。

用户描述：{description or "未提供"}

{DEFAULT_PORTION_HINTS}

完整识别规则（必须遵守）：
1. 尽可能识别图片中的所有食物和配料，包括只占一点点空间的部分：葱花、芝麻、海草、毛豆、黄瓜丝、萝卜丝、炸物碎、蟹棒、沙拉、酱汁、油光、配菜等都要列入 ingredients。
2. 不要只报主食和主蛋白。酱汁、蛋黄酱、油、炸物、小配菜漏掉会导致热量严重偏低。
3. 酱汁/油脂即使看不清具体种类，只要碗里有光泽、浇汁或沙拉感，就必须单独给出一行估计（名称可写“酱汁/调味油”），并给克数和热量。
4. 如果照片里有筷子、叉子、勺子或其他餐具，必须把它们当作尺寸参照来校准碗的大小和食材克重，并在 portion_basis 里简短提到。

份量与热量规则（必须遵守）：
5. 先判断容器是“普通碗”还是“大碗/超大碗”。碗很大、装得很满时，米饭和蛋白必须上调，不能按小份家常碗估算。
6. 每个食材都必须给出 best_estimate_grams、grams_low、grams_high。禁止只写“不确定”而不给数值。
7. 米饭、寿司米、三文鱼、肉类、牛油果、酱汁、油脂、炸物：这些高热量项即使模糊也必须估算；看不清时用上面的大碗默认份量。
8. total_calories 必须等于（或非常接近）各 ingredients 的 calories 之和，基于 best_estimate_grams；禁止另给一个更低的“保险总数”。
9. 严禁系统性低估。对大号 poke bowl / 生鱼片盖饭，主结果常见 950–1200 kcal；像 550–750 这种偏低结果通常是错的，除非碗明显很小、食物很少。
10. calorie_range_low / calorie_range_high 表达不确定；total_calories 取中间偏上的记录值，不是下限。
11. 不确定时宁可略高一点以便用户减重/增肌记账，也不要系统性偏低。

输出要求：
12. uncertainty_factors 用中文说明不确定点，但不能阻止给出数值。
13. portion_basis 说明克重依据；若用了餐具参照，写明“对照筷子/勺子估…”。
14. user_friendly_explanation 用中文列出主要和次要食材，提到是否按大碗/餐具校准，并提醒可手动修正。
15. 数字全部必填；ingredients 宁多勿漏。
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

    # Prefer ingredient sums so missing toppings in the headline total still count.
    model_calories = round(float(payload["total_calories"]), 1)
    calories = model_calories
    protein_g = round(float(payload["protein_g"]), 1)
    carbs_g = round(float(payload["carbs_g"]), 1)
    fat_g = round(float(payload["fat_g"]), 1)
    if summed_calories > 0 and model_calories < summed_calories * 0.95:
        calories = round(summed_calories, 1)
        protein_g = round(summed_protein, 1)
        carbs_g = round(summed_carbs, 1)
        fat_g = round(summed_fat, 1)

    range_low = round(float(payload["calorie_range_low"]), 1)
    range_high = round(float(payload["calorie_range_high"]), 1)
    # Bias the usable logging range upward when the model stays too low.
    if range_high < calories * 1.1:
        range_high = round(calories * 1.2, 1)
    if range_low > calories * 0.9:
        range_low = round(calories * 0.85, 1)
    if range_low > calories:
        range_low = round(calories * 0.85, 1)
    # If the point estimate sits near the bottom of a wide range, nudge it up.
    mid = (range_low + range_high) / 2
    if range_high > range_low and calories < mid * 0.95:
        calories = round((mid + range_high) / 2, 1)

    names = " ".join(match.name for match in matches)
    looks_like_large_bowl = any(
        keyword in names
        for keyword in ("米", "饭", "三文鱼", "刺身", "salmon", "poke")
    )
    if looks_like_large_bowl and calories < 850:
        # Avoid repeating the common 550–750 under-estimate for large fish-rice bowls.
        calories = round(max(calories, min(range_high, 980)), 1)
        if range_high < calories:
            range_high = round(calories * 1.15, 1)
        if range_low > calories * 0.85:
            range_low = round(calories * 0.8, 1)

    explanation = payload["user_friendly_explanation"]
    if portion_notes:
        explanation = (
            f"{explanation} 已尽量计入可见食材，份量取 best estimate："
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
