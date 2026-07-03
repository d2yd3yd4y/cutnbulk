import { ingredients as ingredientDatabase } from "./data/ingredients";
import type { DishTemplate, EstimateResult, IngredientBreakdown, UserModifiers } from "./types";
import { applyModifiers } from "./utils/applyModifiers";
import { calculateConfidence, calorieRange, confidenceLabel } from "./utils/calculateConfidence";
import { matchDish } from "./utils/matchDish";

export function estimateDishNutrition(
  dishName: string,
  modifiers: UserModifiers = {},
): EstimateResult {
  const match = matchDish(dishName);
  if (!match.template) {
    return unknownDishResult(dishName);
  }

  const template = match.template;
  const adjustedPortions = applyModifiers(template.ingredients, modifiers);
  const breakdown = adjustedPortions
    .map((portion): IngredientBreakdown => {
      const nutrition = ingredientDatabase[portion.ingredientId];
      if (!nutrition) {
        throw new Error(`Missing ingredient nutrition: ${portion.ingredientId}`);
      }
      const factor = portion.adjustedGrams / 100;
      return {
        ingredientId: nutrition.id,
        name: nutrition.name,
        defaultGrams: portion.grams,
        adjustedGrams: portion.adjustedGrams,
        calories: round1(nutrition.caloriesPer100g * factor),
        protein: round1(nutrition.proteinPer100g * factor),
        carbs: round1(nutrition.carbsPer100g * factor),
        fat: round1(nutrition.fatPer100g * factor),
        uncertaintyLevel: nutrition.uncertaintyLevel,
        note: portion.note,
      };
    })
    .filter((ingredient) => ingredient.adjustedGrams > 0);

  const totals = sumBreakdown(breakdown);
  const confidenceScore = calculateConfidence(template, breakdown, modifiers);

  return {
    inputDishName: dishName,
    matchedDishName: template.name,
    isUnknown: false,
    totalCalories: totals.totalCalories,
    protein: totals.protein,
    carbs: totals.carbs,
    fat: totals.fat,
    confidenceScore,
    confidenceLabel: confidenceLabel(confidenceScore),
    ingredients: breakdown,
    mainUncertaintyFactors: template.mainUncertaintyFactors,
    calorieRange: calorieRange(totals.totalCalories, confidenceScore),
    userFriendlyExplanation: buildExplanation(template, modifiers, confidenceScore),
  };
}

function sumBreakdown(ingredients: IngredientBreakdown[]) {
  return {
    totalCalories: round1(ingredients.reduce((sum, item) => sum + item.calories, 0)),
    protein: round1(ingredients.reduce((sum, item) => sum + item.protein, 0)),
    carbs: round1(ingredients.reduce((sum, item) => sum + item.carbs, 0)),
    fat: round1(ingredients.reduce((sum, item) => sum + item.fat, 0)),
  };
}

function buildExplanation(
  template: DishTemplate,
  modifiers: UserModifiers,
  confidenceScore: number,
): string {
  const modifierText = describeModifiers(modifiers);
  const uncertainty = template.mainUncertaintyFactors.slice(0, 3).join("、");
  const label =
    confidenceScore >= 0.7
      ? "这个估算相对稳定"
      : confidenceScore >= 0.45
        ? "这个估算适合做日常记录参考"
        : "这类菜波动较大，建议按区间或偏上限记录";

  return `这份${template.name}按${modifierText}估算。主要误差来自${uncertainty}。${label}，结果不是医学级精确值。`;
}

function describeModifiers(modifiers: UserModifiers): string {
  const parts: string[] = [];
  const rice = { low: "少饭", normal: "正常饭量", high: "加饭" }[modifiers.riceAmount ?? "normal"];
  const skin = { none: "不吃皮", half: "吃一半皮", full: "皮全吃" }[modifiers.skinEaten ?? "full"];
  const sauce = { low: "少酱汁", normal: "普通酱汁", high: "多酱汁" }[modifiers.sauceLevel ?? "normal"];
  const oil = { low: "少油", normal: "正常油量", high: "重油" }[modifiers.oilLevel ?? "normal"];
  const portion = { small: "小份", normal: "正常份量", large: "大份" }[modifiers.portionSize ?? "normal"];

  parts.push(portion, rice, sauce, oil);
  if (modifiers.skinEaten) parts.push(skin);
  if (modifiers.crispyType === "none") parts.push("不加薄脆/油条");
  return parts.join("、");
}

function unknownDishResult(dishName: string): EstimateResult {
  return {
    inputDishName: dishName,
    isUnknown: true,
    totalCalories: 0,
    protein: 0,
    carbs: 0,
    fat: 0,
    confidenceScore: 0.2,
    confidenceLabel: "low",
    ingredients: [],
    mainUncertaintyFactors: ["未匹配到菜品模板", "需要用户补充食材或选择相近菜品"],
    calorieRange: { min: 0, max: 0 },
    userFriendlyExplanation: `暂时没有匹配到“${dishName}”的中餐模板。可以先选择相近菜品，或补充原材料后再估算；不要把这个结果当作真实热量。`,
  };
}

function round1(value: number): number {
  return Math.round(value * 10) / 10;
}
