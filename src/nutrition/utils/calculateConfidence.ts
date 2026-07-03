import type { ConfidenceLabel, DishTemplate, IngredientBreakdown, UserModifiers } from "../types";

export function calculateConfidence(
  template: DishTemplate,
  ingredients: IngredientBreakdown[],
  modifiers: UserModifiers = {},
): number {
  let score = template.baseConfidence;

  const modifierCount = Object.values(modifiers).filter(Boolean).length;
  score += Math.min(modifierCount * 0.035, 0.16);

  for (const ingredient of ingredients) {
    if (ingredient.adjustedGrams === 0) continue;
    if (ingredient.uncertaintyLevel === "high") score -= 0.035;
    if (ingredient.uncertaintyLevel === "medium") score -= 0.012;
  }

  const uncertaintyText = template.mainUncertaintyFactors.join("");
  if (uncertaintyText.includes("油")) score -= 0.04;
  if (uncertaintyText.includes("酱")) score -= 0.035;
  if (template.complexity === "hotpot") score -= 0.08;

  return clamp(round2(score), 0.2, 0.9);
}

export function confidenceLabel(score: number): ConfidenceLabel {
  if (score >= 0.7) return "high";
  if (score >= 0.45) return "medium";
  return "low";
}

export function calorieRange(totalCalories: number, confidenceScore: number): { min: number; max: number } {
  const spread = confidenceScore >= 0.7 ? 0.12 : confidenceScore >= 0.45 ? 0.22 : 0.36;
  return {
    min: Math.max(0, Math.round(totalCalories * (1 - spread))),
    max: Math.round(totalCalories * (1 + spread)),
  };
}

function clamp(value: number, min: number, max: number): number {
  return Math.min(max, Math.max(min, value));
}

function round2(value: number): number {
  return Math.round(value * 100) / 100;
}
