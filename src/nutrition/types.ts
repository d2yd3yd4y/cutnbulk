export type UncertaintyLevel = "low" | "medium" | "high";

export type ConfidenceLabel = "high" | "medium" | "low";

export type DishComplexity =
  | "standard"
  | "single_breakfast"
  | "takeout_combo"
  | "hotpot";

export type ModifierKey =
  | "riceAmount"
  | "skinEaten"
  | "sauceLevel"
  | "oilLevel"
  | "portionSize"
  | "crispyType";

export interface IngredientNutrition {
  id: string;
  name: string;
  caloriesPer100g: number;
  proteinPer100g: number;
  carbsPer100g: number;
  fatPer100g: number;
  uncertaintyLevel: UncertaintyLevel;
}

export interface IngredientPortion {
  ingredientId: string;
  grams: number;
  note?: string;
  affectedBy?: ModifierKey[];
}

export interface DishTemplate {
  id: string;
  name: string;
  aliases: string[];
  complexity: DishComplexity;
  baseConfidence: number;
  ingredients: IngredientPortion[];
  mainUncertaintyFactors: string[];
}

export interface UserModifiers {
  riceAmount?: "low" | "normal" | "high";
  skinEaten?: "none" | "half" | "full";
  sauceLevel?: "low" | "normal" | "high";
  oilLevel?: "low" | "normal" | "high";
  portionSize?: "small" | "normal" | "large";
  crispyType?: "crispy_cracker" | "none";
}

export interface IngredientBreakdown {
  ingredientId: string;
  name: string;
  defaultGrams: number;
  adjustedGrams: number;
  calories: number;
  protein: number;
  carbs: number;
  fat: number;
  uncertaintyLevel: UncertaintyLevel;
  note?: string;
}

export interface CalorieRange {
  min: number;
  max: number;
}

export interface EstimateResult {
  inputDishName: string;
  matchedDishName?: string;
  isUnknown: boolean;
  totalCalories: number;
  protein: number;
  carbs: number;
  fat: number;
  confidenceScore: number;
  confidenceLabel: ConfidenceLabel;
  ingredients: IngredientBreakdown[];
  mainUncertaintyFactors: string[];
  calorieRange: CalorieRange;
  userFriendlyExplanation: string;
}
