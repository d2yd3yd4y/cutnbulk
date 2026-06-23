from dataclasses import dataclass


@dataclass(frozen=True)
class NutritionEstimate:
    calories: float
    protein_g: float
    carbs_g: float
    fat_g: float
    confidence: float
    reasoning: str
