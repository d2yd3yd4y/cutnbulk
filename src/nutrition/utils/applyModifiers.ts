import type { IngredientPortion, UserModifiers } from "../types";

const riceMultipliers = {
  low: 0.65,
  normal: 1,
  high: 1.35,
} as const;

const skinMultipliers = {
  none: 0,
  half: 0.5,
  full: 1,
} as const;

const sauceMultipliers = {
  low: 0.6,
  normal: 1,
  high: 1.5,
} as const;

const oilMultipliers = {
  low: 0.5,
  normal: 1,
  high: 1.8,
} as const;

const portionMultipliers = {
  small: 0.85,
  normal: 1,
  large: 1.2,
} as const;

export interface AdjustedPortion extends IngredientPortion {
  adjustedGrams: number;
}

/**
 * Applies user-visible variables to ingredient grams. The template remains the
 * source of truth; modifiers only adjust known high-impact parts.
 */
export function applyModifiers(
  portions: IngredientPortion[],
  modifiers: UserModifiers = {},
): AdjustedPortion[] {
  return portions.map((portion) => {
    let grams = portion.grams;
    const affectedBy = portion.affectedBy ?? [];

    if (affectedBy.includes("portionSize")) {
      grams *= portionMultipliers[modifiers.portionSize ?? "normal"];
    }
    if (affectedBy.includes("riceAmount")) {
      grams *= riceMultipliers[modifiers.riceAmount ?? "normal"];
    }
    if (affectedBy.includes("skinEaten")) {
      grams *= skinMultipliers[modifiers.skinEaten ?? "full"];
    }
    if (affectedBy.includes("sauceLevel")) {
      grams *= sauceMultipliers[modifiers.sauceLevel ?? "normal"];
    }
    if (affectedBy.includes("oilLevel")) {
      grams *= oilMultipliers[modifiers.oilLevel ?? "normal"];
    }
    if (affectedBy.includes("crispyType") && modifiers.crispyType === "none") {
      grams = 0;
    }

    return {
      ...portion,
      adjustedGrams: round1(grams),
    };
  });
}

function round1(value: number): number {
  return Math.round(value * 10) / 10;
}
