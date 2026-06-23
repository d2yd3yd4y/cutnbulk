import os
from dataclasses import asdict

from app.schemas import NutritionEstimate


TEMPLATE_ESTIMATES = {
    "鸡胸肉 + 米饭 + 西兰花": NutritionEstimate(520, 45, 58, 10, 0.82, "按常见健身餐份量估算。"),
    "牛肉面": NutritionEstimate(680, 32, 92, 20, 0.76, "按一碗普通牛肉面估算。"),
    "黄焖鸡米饭": NutritionEstimate(780, 38, 96, 26, 0.74, "按一份外卖黄焖鸡米饭估算。"),
    "沙拉 + 鸡蛋": NutritionEstimate(360, 20, 24, 20, 0.78, "按含两个鸡蛋和少量酱汁的沙拉估算。"),
    "蛋白粉": NutritionEstimate(130, 25, 4, 2, 0.9, "按一勺乳清蛋白估算。"),
    "奶茶": NutritionEstimate(420, 6, 62, 16, 0.65, "按中杯含糖奶茶估算。"),
}


def estimate_food_nutrition(
    description: str,
    image_path: str | None = None,
) -> NutritionEstimate:
    """可替换的饮食估算入口。

    第一版默认使用规则和模板做本地 mock。之后如果配置 OPENAI_API_KEY，
    可以在这里接入 Vision API，并保持返回结构不变。
    """
    if os.getenv("OPENAI_API_KEY"):
        return _estimate_with_openai_placeholder(description, image_path)
    return _estimate_with_mock(description, image_path)


def estimate_food_nutrition_dict(
    description: str,
    image_path: str | None = None,
) -> dict[str, float | str]:
    return asdict(estimate_food_nutrition(description, image_path))


def _estimate_with_mock(description: str, image_path: str | None) -> NutritionEstimate:
    normalized = (description or "").strip()
    if normalized in TEMPLATE_ESTIMATES:
        return TEMPLATE_ESTIMATES[normalized]

    text = normalized.lower()
    calories = 360.0
    protein = 18.0
    carbs = 42.0
    fat = 12.0
    reasons = ["根据文字描述使用本地规则估算。"]

    adjustments = [
        (("米饭", "面", "馒头", "粥", "粉", "土豆", "红薯"), 150, 3, 34, 1, "包含主食"),
        (("鸡胸", "鸡肉", "牛肉", "鱼", "虾", "鸡蛋", "蛋白"), 120, 22, 2, 5, "包含明显蛋白质来源"),
        (("奶茶", "拿铁", "甜品", "蛋糕", "饼干"), 220, 5, 32, 8, "包含饮品或甜食"),
        (("沙拉", "西兰花", "蔬菜", "青菜"), 60, 4, 10, 1, "包含蔬菜"),
        (("油炸", "炸鸡", "薯条", "汉堡"), 260, 12, 24, 16, "可能含较多脂肪"),
    ]
    for keywords, add_calories, add_protein, add_carbs, add_fat, reason in adjustments:
        if any(keyword in text for keyword in keywords):
            calories += add_calories
            protein += add_protein
            carbs += add_carbs
            fat += add_fat
            reasons.append(reason)

    if image_path:
        calories += 80
        carbs += 8
        fat += 4
        reasons.append("已上传照片，第一版先按普通份量略作修正")

    return NutritionEstimate(
        calories=round(calories, 1),
        protein_g=round(protein, 1),
        carbs_g=round(carbs, 1),
        fat_g=round(fat, 1),
        confidence=0.55,
        reasoning="；".join(reasons),
    )


def _estimate_with_openai_placeholder(
    description: str,
    image_path: str | None,
) -> NutritionEstimate:
    # 预留真实 OpenAI Vision 接入点；MVP 中保持本地可运行，不强制联网或配置密钥。
    estimate = _estimate_with_mock(description, image_path)
    return NutritionEstimate(
        calories=estimate.calories,
        protein_g=estimate.protein_g,
        carbs_g=estimate.carbs_g,
        fat_g=estimate.fat_g,
        confidence=max(estimate.confidence, 0.6),
        reasoning=f"{estimate.reasoning}；已检测到 OPENAI_API_KEY，当前版本仍使用本地估算占位逻辑。",
    )
