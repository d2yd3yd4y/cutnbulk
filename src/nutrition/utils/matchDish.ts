import { dishTemplates } from "../data/dishTemplates";
import type { DishTemplate } from "../types";

function normalizeDishName(value: string): string {
  return value
    .toLowerCase()
    .replace(/[，。、“”‘’\s\-_/()（）]/g, "")
    .trim();
}

function charOverlapScore(input: string, candidate: string): number {
  if (!input || !candidate) return 0;
  const inputChars = new Set([...input]);
  const candidateChars = new Set([...candidate]);
  let overlap = 0;
  for (const char of inputChars) {
    if (candidateChars.has(char)) overlap += 1;
  }
  return overlap / Math.max(inputChars.size, candidateChars.size);
}

export interface DishMatch {
  template?: DishTemplate;
  score: number;
  matchedBy: "exact" | "contains" | "fuzzy" | "none";
}

/**
 * Matches exact aliases first, then containment, then a small character-overlap
 * fuzzy score. This is intentionally simple and deterministic for MVP.
 */
export function matchDish(dishName: string): DishMatch {
  const normalizedInput = normalizeDishName(dishName);
  if (!normalizedInput) return { score: 0, matchedBy: "none" };

  let best: DishMatch = { score: 0, matchedBy: "none" };

  for (const template of dishTemplates) {
    const names = [template.name, ...template.aliases].map(normalizeDishName);
    for (const name of names) {
      if (normalizedInput === name) {
        return { template, score: 1, matchedBy: "exact" };
      }
      if (normalizedInput.includes(name) || name.includes(normalizedInput)) {
        const score = Math.min(normalizedInput.length, name.length) / Math.max(normalizedInput.length, name.length);
        if (score > best.score) best = { template, score, matchedBy: "contains" };
      }
      const fuzzyScore = charOverlapScore(normalizedInput, name);
      if (fuzzyScore > best.score) {
        best = { template, score: fuzzyScore, matchedBy: "fuzzy" };
      }
    }
  }

  return best.score >= 0.42 ? best : { score: best.score, matchedBy: "none" };
}
