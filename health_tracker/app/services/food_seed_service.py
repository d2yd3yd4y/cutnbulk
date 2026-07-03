import json
import re

from sqlalchemy.orm import Session

from app.models import FoodItem


def normalize_food_name(value: str) -> str:
    return re.sub(r"\s+", "", value.strip().lower())


def seed_food_database(db: Session) -> int:
    inserted = 0
    existing = {
        item.normalized_name for item in db.query(FoodItem.normalized_name).all()
    }
    for item in SEED_FOOD_ITEMS:
        normalized = normalize_food_name(item["name"])
        if normalized in existing:
            continue
        db.add(
            FoodItem(
                name=item["name"],
                normalized_name=normalized,
                aliases=json.dumps(item.get("aliases", []), ensure_ascii=False),
                category=item["category"],
                cuisine=item.get("cuisine", ""),
                serving_desc=item.get("serving_desc", "100g"),
                serving_grams=item.get("serving_grams", 100),
                calories_per_100g=item["calories"],
                protein_per_100g=item["protein"],
                carbs_per_100g=item["carbs"],
                fat_per_100g=item["fat"],
                fiber_per_100g=item.get("fiber"),
                sodium_per_100g=item.get("sodium"),
                source="seed/manual",
                confidence=item.get("confidence", 0.7),
                notes=item.get("notes"),
            )
        )
        existing.add(normalized)
        inserted += 1
    if inserted:
        db.commit()
    return inserted


CHINESE_DISH_NOTE = "按常见外卖/家常平均值估算，实际会受油量、酱料和份量影响。"

SEED_FOOD_ITEMS = [
    # 基础主食
    {"name": "米饭", "aliases": ["白米饭", "熟米饭", "rice", "cooked rice"], "category": "主食", "cuisine": "中国", "serving_desc": "一碗", "serving_grams": 200, "calories": 116, "protein": 2.6, "carbs": 25.9, "fat": 0.3, "confidence": 0.9},
    {"name": "糙米饭", "aliases": ["糙米", "brown rice"], "category": "主食", "cuisine": "通用", "serving_desc": "一碗", "serving_grams": 200, "calories": 111, "protein": 2.6, "carbs": 23.0, "fat": 0.9, "fiber": 1.8, "confidence": 0.85},
    {"name": "馒头", "aliases": ["白馒头", "steamed bun"], "category": "主食", "cuisine": "中国", "serving_desc": "一个", "serving_grams": 100, "calories": 223, "protein": 7.0, "carbs": 47.0, "fat": 1.0, "confidence": 0.82},
    {"name": "面条", "aliases": ["熟面条", "noodles"], "category": "主食", "cuisine": "通用", "serving_desc": "一碗", "serving_grams": 250, "calories": 138, "protein": 4.5, "carbs": 25.0, "fat": 2.1, "confidence": 0.78},
    {"name": "米粉", "aliases": ["rice noodles"], "category": "主食", "cuisine": "中国", "serving_desc": "一碗", "serving_grams": 250, "calories": 110, "protein": 1.8, "carbs": 24.0, "fat": 0.6, "confidence": 0.75},
    {"name": "河粉", "aliases": ["宽粉", "flat rice noodles"], "category": "主食", "cuisine": "中国", "serving_desc": "一碗", "serving_grams": 250, "calories": 135, "protein": 2.4, "carbs": 29.0, "fat": 0.8, "confidence": 0.75},
    {"name": "红薯", "aliases": ["地瓜", "sweet potato"], "category": "主食", "cuisine": "通用", "serving_desc": "一个中等", "serving_grams": 180, "calories": 86, "protein": 1.6, "carbs": 20.1, "fat": 0.1, "fiber": 3.0, "confidence": 0.9},
    {"name": "土豆", "aliases": ["马铃薯", "potato"], "category": "主食", "cuisine": "通用", "serving_desc": "一个中等", "serving_grams": 180, "calories": 77, "protein": 2.0, "carbs": 17.0, "fat": 0.1, "confidence": 0.9},
    {"name": "玉米", "aliases": ["甜玉米", "corn"], "category": "主食", "cuisine": "通用", "serving_desc": "一根", "serving_grams": 180, "calories": 96, "protein": 3.4, "carbs": 21.0, "fat": 1.5, "confidence": 0.85},
    {"name": "燕麦", "aliases": ["生燕麦", "燕麦片", "oats", "oatmeal"], "category": "主食", "cuisine": "通用", "serving_desc": "50g", "serving_grams": 50, "calories": 389, "protein": 16.9, "carbs": 66.3, "fat": 6.9, "fiber": 10.6, "confidence": 0.9},
    {"name": "全麦面包", "aliases": ["whole wheat bread"], "category": "主食", "cuisine": "西式", "serving_desc": "两片", "serving_grams": 60, "calories": 247, "protein": 13.0, "carbs": 41.0, "fat": 4.2, "confidence": 0.82},
    {"name": "白面包", "aliases": ["吐司", "white bread"], "category": "主食", "cuisine": "西式", "serving_desc": "两片", "serving_grams": 60, "calories": 265, "protein": 9.0, "carbs": 49.0, "fat": 3.2, "confidence": 0.82},
    {"name": "饺子", "aliases": ["水饺", "dumplings"], "category": "主食", "cuisine": "中国", "serving_desc": "一份", "serving_grams": 250, "calories": 220, "protein": 8.0, "carbs": 28.0, "fat": 8.0, "confidence": 0.65, "notes": CHINESE_DISH_NOTE},
    {"name": "包子", "aliases": ["肉包", "菜包", "baozi"], "category": "早餐", "cuisine": "中国", "serving_desc": "一个", "serving_grams": 100, "calories": 230, "protein": 7.0, "carbs": 35.0, "fat": 7.0, "confidence": 0.68, "notes": CHINESE_DISH_NOTE},
    {"name": "粥", "aliases": ["白粥", "porridge"], "category": "主食", "cuisine": "中国", "serving_desc": "一碗", "serving_grams": 300, "calories": 46, "protein": 1.1, "carbs": 10.0, "fat": 0.2, "confidence": 0.8},
    # 蛋白质食材
    {"name": "鸡胸肉", "aliases": ["鸡胸", "chicken breast"], "category": "肉类", "cuisine": "通用", "serving_desc": "一份", "serving_grams": 150, "calories": 165, "protein": 31.0, "carbs": 0, "fat": 3.6, "confidence": 0.9},
    {"name": "鸡腿肉", "aliases": ["鸡腿", "chicken thigh"], "category": "肉类", "cuisine": "通用", "serving_desc": "一份", "serving_grams": 150, "calories": 209, "protein": 26.0, "carbs": 0, "fat": 10.9, "confidence": 0.85},
    {"name": "牛肉", "aliases": ["瘦牛肉", "beef"], "category": "肉类", "cuisine": "通用", "serving_desc": "一份", "serving_grams": 150, "calories": 250, "protein": 26.0, "carbs": 0, "fat": 15.0, "confidence": 0.82},
    {"name": "牛腩", "aliases": ["beef brisket"], "category": "肉类", "cuisine": "通用", "serving_desc": "一份", "serving_grams": 150, "calories": 332, "protein": 18.0, "carbs": 0, "fat": 28.0, "confidence": 0.78},
    {"name": "猪里脊", "aliases": ["猪里脊肉", "pork tenderloin"], "category": "肉类", "cuisine": "通用", "serving_desc": "一份", "serving_grams": 150, "calories": 143, "protein": 26.0, "carbs": 0, "fat": 3.5, "confidence": 0.85},
    {"name": "猪五花", "aliases": ["五花肉", "pork belly"], "category": "肉类", "cuisine": "通用", "serving_desc": "一份", "serving_grams": 120, "calories": 518, "protein": 9.3, "carbs": 0, "fat": 53.0, "confidence": 0.8},
    {"name": "鸡蛋", "aliases": ["全蛋", "egg"], "category": "蛋类", "cuisine": "通用", "serving_desc": "一个", "serving_grams": 50, "calories": 143, "protein": 12.6, "carbs": 0.7, "fat": 9.5, "confidence": 0.9},
    {"name": "蛋清", "aliases": ["蛋白", "egg white"], "category": "蛋类", "cuisine": "通用", "serving_desc": "一个蛋清", "serving_grams": 33, "calories": 52, "protein": 10.9, "carbs": 0.7, "fat": 0.2, "confidence": 0.9},
    {"name": "三文鱼", "aliases": ["salmon"], "category": "鱼类", "cuisine": "通用", "serving_desc": "一份", "serving_grams": 150, "calories": 208, "protein": 20.0, "carbs": 0, "fat": 13.0, "confidence": 0.86},
    {"name": "鳕鱼", "aliases": ["cod"], "category": "鱼类", "cuisine": "通用", "serving_desc": "一份", "serving_grams": 150, "calories": 82, "protein": 18.0, "carbs": 0, "fat": 0.7, "confidence": 0.86},
    {"name": "虾", "aliases": ["shrimp", "prawn"], "category": "海鲜", "cuisine": "通用", "serving_desc": "一份", "serving_grams": 120, "calories": 99, "protein": 24.0, "carbs": 0.2, "fat": 0.3, "confidence": 0.86},
    {"name": "豆腐", "aliases": ["tofu"], "category": "豆制品", "cuisine": "中国", "serving_desc": "一份", "serving_grams": 150, "calories": 76, "protein": 8.0, "carbs": 1.9, "fat": 4.8, "confidence": 0.85},
    {"name": "豆干", "aliases": ["豆腐干"], "category": "豆制品", "cuisine": "中国", "serving_desc": "一份", "serving_grams": 100, "calories": 150, "protein": 16.0, "carbs": 9.0, "fat": 6.0, "confidence": 0.78},
    {"name": "牛奶", "aliases": ["纯牛奶", "milk"], "category": "饮品", "cuisine": "通用", "serving_desc": "一杯", "serving_grams": 250, "calories": 61, "protein": 3.2, "carbs": 4.8, "fat": 3.3, "confidence": 0.85},
    {"name": "希腊酸奶", "aliases": ["greek yogurt"], "category": "乳制品", "cuisine": "西式", "serving_desc": "一杯", "serving_grams": 170, "calories": 97, "protein": 9.0, "carbs": 3.6, "fat": 5.0, "confidence": 0.82},
    {"name": "蛋白粉", "aliases": ["乳清蛋白", "whey protein", "protein powder"], "category": "补剂", "cuisine": "通用", "serving_desc": "一勺", "serving_grams": 30, "calories": 400, "protein": 80.0, "carbs": 8.0, "fat": 6.0, "confidence": 0.82},
    # 常见中餐菜品和外卖
    {"name": "宫保鸡丁", "aliases": ["kung pao chicken"], "category": "中餐菜品", "cuisine": "川菜", "serving_desc": "一份", "serving_grams": 300, "calories": 210, "protein": 14, "carbs": 12, "fat": 12, "confidence": 0.6, "notes": CHINESE_DISH_NOTE},
    {"name": "鱼香肉丝", "aliases": [], "category": "中餐菜品", "cuisine": "川菜", "serving_desc": "一份", "serving_grams": 300, "calories": 190, "protein": 12, "carbs": 15, "fat": 10, "confidence": 0.6, "notes": CHINESE_DISH_NOTE},
    {"name": "回锅肉", "aliases": [], "category": "中餐菜品", "cuisine": "川菜", "serving_desc": "一份", "serving_grams": 280, "calories": 310, "protein": 12, "carbs": 8, "fat": 26, "confidence": 0.58, "notes": CHINESE_DISH_NOTE},
    {"name": "红烧肉", "aliases": [], "category": "中餐菜品", "cuisine": "中国", "serving_desc": "一份", "serving_grams": 250, "calories": 420, "protein": 12, "carbs": 8, "fat": 38, "confidence": 0.55, "notes": CHINESE_DISH_NOTE},
    {"name": "红烧牛肉", "aliases": [], "category": "中餐菜品", "cuisine": "中国", "serving_desc": "一份", "serving_grams": 300, "calories": 260, "protein": 18, "carbs": 7, "fat": 17, "confidence": 0.6, "notes": CHINESE_DISH_NOTE},
    {"name": "番茄炒蛋", "aliases": ["西红柿炒鸡蛋", "西红柿炒蛋"], "category": "中餐菜品", "cuisine": "中国", "serving_desc": "一份", "serving_grams": 300, "calories": 150, "protein": 7, "carbs": 8, "fat": 10, "confidence": 0.68, "notes": CHINESE_DISH_NOTE},
    {"name": "青椒肉丝", "aliases": [], "category": "中餐菜品", "cuisine": "中国", "serving_desc": "一份", "serving_grams": 300, "calories": 180, "protein": 13, "carbs": 8, "fat": 11, "confidence": 0.62, "notes": CHINESE_DISH_NOTE},
    {"name": "麻婆豆腐", "aliases": [], "category": "中餐菜品", "cuisine": "川菜", "serving_desc": "一份", "serving_grams": 300, "calories": 170, "protein": 9, "carbs": 8, "fat": 11, "confidence": 0.63, "notes": CHINESE_DISH_NOTE},
    {"name": "西红柿牛腩", "aliases": ["番茄牛腩"], "category": "中餐菜品", "cuisine": "中国", "serving_desc": "一份", "serving_grams": 350, "calories": 185, "protein": 12, "carbs": 8, "fat": 11, "confidence": 0.62, "notes": CHINESE_DISH_NOTE},
    {"name": "土豆牛肉", "aliases": ["牛肉炖土豆"], "category": "中餐菜品", "cuisine": "中国", "serving_desc": "一份", "serving_grams": 350, "calories": 180, "protein": 11, "carbs": 14, "fat": 9, "confidence": 0.62, "notes": CHINESE_DISH_NOTE},
    {"name": "清炒西兰花", "aliases": ["西兰花"], "category": "蔬菜", "cuisine": "中国", "serving_desc": "一份", "serving_grams": 200, "calories": 70, "protein": 3.5, "carbs": 7, "fat": 3.5, "confidence": 0.72, "notes": CHINESE_DISH_NOTE},
    {"name": "蒜蓉青菜", "aliases": ["青菜"], "category": "蔬菜", "cuisine": "中国", "serving_desc": "一份", "serving_grams": 200, "calories": 65, "protein": 2.5, "carbs": 6, "fat": 3.5, "confidence": 0.72, "notes": CHINESE_DISH_NOTE},
    {"name": "地三鲜", "aliases": [], "category": "中餐菜品", "cuisine": "东北菜", "serving_desc": "一份", "serving_grams": 320, "calories": 185, "protein": 3, "carbs": 20, "fat": 10, "confidence": 0.58, "notes": CHINESE_DISH_NOTE},
    {"name": "炒饭", "aliases": ["fried rice"], "category": "主食", "cuisine": "中国", "serving_desc": "一份", "serving_grams": 350, "calories": 180, "protein": 5, "carbs": 28, "fat": 5, "confidence": 0.65, "notes": CHINESE_DISH_NOTE},
    {"name": "蛋炒饭", "aliases": [], "category": "主食", "cuisine": "中国", "serving_desc": "一份", "serving_grams": 380, "calories": 190, "protein": 6, "carbs": 28, "fat": 6, "confidence": 0.65, "notes": CHINESE_DISH_NOTE},
    {"name": "牛肉炒饭", "aliases": [], "category": "主食", "cuisine": "中国", "serving_desc": "一份", "serving_grams": 400, "calories": 205, "protein": 8, "carbs": 27, "fat": 7, "confidence": 0.62, "notes": CHINESE_DISH_NOTE},
    {"name": "炒面", "aliases": [], "category": "主食", "cuisine": "中国", "serving_desc": "一份", "serving_grams": 400, "calories": 190, "protein": 6, "carbs": 27, "fat": 6, "confidence": 0.62, "notes": CHINESE_DISH_NOTE},
    {"name": "牛肉面", "aliases": [], "category": "面食", "cuisine": "中国", "serving_desc": "一份", "serving_grams": 600, "calories": 110, "protein": 6, "carbs": 16, "fat": 2.5, "confidence": 0.62, "notes": CHINESE_DISH_NOTE},
    {"name": "兰州拉面", "aliases": ["拉面"], "category": "面食", "cuisine": "西北", "serving_desc": "一碗", "serving_grams": 600, "calories": 105, "protein": 5.5, "carbs": 17, "fat": 2, "confidence": 0.6, "notes": CHINESE_DISH_NOTE},
    {"name": "重庆小面", "aliases": ["小面"], "category": "面食", "cuisine": "川渝", "serving_desc": "一碗", "serving_grams": 500, "calories": 155, "protein": 5, "carbs": 22, "fat": 5, "confidence": 0.58, "notes": CHINESE_DISH_NOTE},
    {"name": "酸辣粉", "aliases": [], "category": "粉面", "cuisine": "川渝", "serving_desc": "一碗", "serving_grams": 500, "calories": 145, "protein": 3, "carbs": 24, "fat": 4.5, "confidence": 0.58, "notes": CHINESE_DISH_NOTE},
    {"name": "黄焖鸡米饭", "aliases": ["黄焖鸡"], "category": "外卖", "cuisine": "中国", "serving_desc": "一份外卖", "serving_grams": 650, "calories": 160, "protein": 8, "carbs": 19, "fat": 5.5, "confidence": 0.6, "notes": CHINESE_DISH_NOTE},
    {"name": "沙县鸡腿饭", "aliases": ["鸡腿饭"], "category": "外卖", "cuisine": "中国", "serving_desc": "一份外卖", "serving_grams": 650, "calories": 170, "protein": 8, "carbs": 21, "fat": 5.5, "confidence": 0.58, "notes": CHINESE_DISH_NOTE},
    {"name": "盖浇饭", "aliases": [], "category": "外卖", "cuisine": "中国", "serving_desc": "一份外卖", "serving_grams": 650, "calories": 165, "protein": 7, "carbs": 22, "fat": 5, "confidence": 0.55, "notes": CHINESE_DISH_NOTE},
    {"name": "麻辣烫", "aliases": [], "category": "外卖", "cuisine": "川渝", "serving_desc": "一份", "serving_grams": 700, "calories": 120, "protein": 6, "carbs": 12, "fat": 5, "confidence": 0.5, "notes": CHINESE_DISH_NOTE},
    {"name": "火锅", "aliases": ["hot pot"], "category": "火锅", "cuisine": "中国", "serving_desc": "一份", "serving_grams": 800, "calories": 180, "protein": 10, "carbs": 8, "fat": 12, "confidence": 0.48, "notes": "按单人常见摄入估算，锅底、蘸料和食材差异很大。"},
    {"name": "烤鱼", "aliases": [], "category": "中餐菜品", "cuisine": "中国", "serving_desc": "一份", "serving_grams": 500, "calories": 180, "protein": 14, "carbs": 6, "fat": 11, "confidence": 0.55, "notes": CHINESE_DISH_NOTE},
    {"name": "烧烤", "aliases": ["烤串"], "category": "烧烤", "cuisine": "中国", "serving_desc": "一份", "serving_grams": 300, "calories": 260, "protein": 18, "carbs": 8, "fat": 17, "confidence": 0.48, "notes": "按混合肉串和少量主食估算，实际差异很大。"},
    {"name": "炸鸡", "aliases": ["fried chicken"], "category": "快餐", "cuisine": "美式", "serving_desc": "一份", "serving_grams": 250, "calories": 290, "protein": 18, "carbs": 10, "fat": 20, "confidence": 0.6},
    {"name": "汉堡", "aliases": ["burger"], "category": "快餐", "cuisine": "美式", "serving_desc": "一个", "serving_grams": 220, "calories": 250, "protein": 12, "carbs": 25, "fat": 12, "confidence": 0.6},
    {"name": "披萨", "aliases": ["pizza"], "category": "西餐", "cuisine": "意式", "serving_desc": "两片", "serving_grams": 200, "calories": 266, "protein": 11, "carbs": 33, "fat": 10, "confidence": 0.65},
    {"name": "沙拉", "aliases": ["salad"], "category": "西餐", "cuisine": "西式", "serving_desc": "一份", "serving_grams": 350, "calories": 90, "protein": 5, "carbs": 8, "fat": 5, "confidence": 0.62, "notes": "酱汁会显著影响热量。"},
    # 早餐/饮品/零食
    {"name": "豆浆", "aliases": ["soy milk"], "category": "饮品", "cuisine": "中国", "serving_desc": "一杯", "serving_grams": 300, "calories": 33, "protein": 3, "carbs": 3, "fat": 1.5, "confidence": 0.78},
    {"name": "油条", "aliases": [], "category": "早餐", "cuisine": "中国", "serving_desc": "一根", "serving_grams": 70, "calories": 388, "protein": 6, "carbs": 50, "fat": 18, "confidence": 0.7},
    {"name": "茶叶蛋", "aliases": [], "category": "早餐", "cuisine": "中国", "serving_desc": "一个", "serving_grams": 55, "calories": 150, "protein": 12, "carbs": 1, "fat": 10, "confidence": 0.78},
    {"name": "煎饼果子", "aliases": ["煎饼"], "category": "早餐", "cuisine": "中国", "serving_desc": "一个", "serving_grams": 250, "calories": 230, "protein": 8, "carbs": 32, "fat": 8, "confidence": 0.55, "notes": CHINESE_DISH_NOTE},
    {"name": "肉夹馍", "aliases": [], "category": "早餐", "cuisine": "西北", "serving_desc": "一个", "serving_grams": 180, "calories": 260, "protein": 12, "carbs": 30, "fat": 10, "confidence": 0.6},
    {"name": "奶茶", "aliases": ["bubble tea", "珍珠奶茶"], "category": "奶茶", "cuisine": "饮品", "serving_desc": "一杯", "serving_grams": 500, "calories": 84, "protein": 1.2, "carbs": 12.5, "fat": 3.2, "confidence": 0.5, "notes": "按中杯常规糖估算，糖度和小料影响很大。"},
    {"name": "拿铁", "aliases": ["latte"], "category": "饮品", "cuisine": "西式", "serving_desc": "一杯", "serving_grams": 350, "calories": 45, "protein": 2.5, "carbs": 4.5, "fat": 2, "confidence": 0.7},
    {"name": "美式咖啡", "aliases": ["americano", "黑咖啡"], "category": "饮品", "cuisine": "西式", "serving_desc": "一杯", "serving_grams": 350, "calories": 2, "protein": 0.1, "carbs": 0, "fat": 0, "confidence": 0.85},
    {"name": "可乐", "aliases": ["cola"], "category": "饮品", "cuisine": "通用", "serving_desc": "一瓶", "serving_grams": 500, "calories": 42, "protein": 0, "carbs": 10.6, "fat": 0, "confidence": 0.85},
    {"name": "酸奶", "aliases": ["yogurt"], "category": "乳制品", "cuisine": "通用", "serving_desc": "一杯", "serving_grams": 180, "calories": 72, "protein": 3.5, "carbs": 9, "fat": 2.5, "confidence": 0.75},
    {"name": "香蕉", "aliases": ["banana"], "category": "水果", "cuisine": "通用", "serving_desc": "一根", "serving_grams": 120, "calories": 89, "protein": 1.1, "carbs": 22.8, "fat": 0.3, "confidence": 0.9},
    {"name": "苹果", "aliases": ["apple"], "category": "水果", "cuisine": "通用", "serving_desc": "一个", "serving_grams": 180, "calories": 52, "protein": 0.3, "carbs": 13.8, "fat": 0.2, "confidence": 0.9},
    {"name": "坚果", "aliases": ["mixed nuts", "nuts"], "category": "零食", "cuisine": "通用", "serving_desc": "一把", "serving_grams": 30, "calories": 607, "protein": 20, "carbs": 21, "fat": 54, "confidence": 0.75},
    {"name": "巧克力", "aliases": ["chocolate"], "category": "零食", "cuisine": "通用", "serving_desc": "一条", "serving_grams": 40, "calories": 546, "protein": 4.9, "carbs": 61, "fat": 31, "confidence": 0.75},
    {"name": "薯片", "aliases": ["potato chips", "chips"], "category": "零食", "cuisine": "通用", "serving_desc": "一包", "serving_grams": 70, "calories": 536, "protein": 7, "carbs": 53, "fat": 35, "confidence": 0.75},
]
