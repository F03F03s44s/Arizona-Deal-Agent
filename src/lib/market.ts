import type { Category } from "./types";

export type MarketComp = {
  id: string;
  pattern: RegExp;
  category: Category;
  marketPrice: number;
  resaleHaircut: number;
};

/**
 * Typical Arizona street / retail prices used as comps.
 * Haircut is the fraction a flipper can usually keep after fees and time.
 */
export const MARKET_COMPS: MarketComp[] = [
  { id: "window-ac", pattern: /\b(window|portable)\b.*\b(a\/?c|air ?condition)/i, category: "cooling", marketPrice: 280, resaleHaircut: 0.78 },
  { id: "mini-split", pattern: /\bmini[- ]?split\b/i, category: "cooling", marketPrice: 1200, resaleHaircut: 0.72 },
  { id: "swamp-cooler", pattern: /\b(swamp|evaporative)\s+cooler\b/i, category: "cooling", marketPrice: 220, resaleHaircut: 0.8 },
  { id: "ceiling-fan", pattern: /\bceiling fan\b/i, category: "cooling", marketPrice: 130, resaleHaircut: 0.7 },
  { id: "tower-fan", pattern: /\b(tower|box) fan\b/i, category: "cooling", marketPrice: 55, resaleHaircut: 0.65 },
  { id: "patio-umbrella", pattern: /\b(patio|market)\b[\w\s-]{0,24}\bumbrellas?\b/i, category: "outdoor", marketPrice: 180, resaleHaircut: 0.7 },
  { id: "canopy", pattern: /\b(pop[- ]?up )?canopy|gazebo|sun sail\b/i, category: "outdoor", marketPrice: 160, resaleHaircut: 0.72 },
  { id: "patio-set", pattern: /\bpatio (set|furniture|table|dining)\b/i, category: "outdoor", marketPrice: 450, resaleHaircut: 0.7 },
  { id: "pool-pump", pattern: /\bpool pump\b/i, category: "outdoor", marketPrice: 280, resaleHaircut: 0.75 },
  { id: "mister", pattern: /\bmist(er|ing)\b/i, category: "outdoor", marketPrice: 90, resaleHaircut: 0.7 },
  { id: "civic", pattern: /\b(honda )?civic\b/i, category: "vehicles", marketPrice: 14500, resaleHaircut: 0.92 },
  { id: "camry", pattern: /\b(toyota )?camry\b/i, category: "vehicles", marketPrice: 15000, resaleHaircut: 0.92 },
  { id: "f150", pattern: /\bf-?150\b/i, category: "vehicles", marketPrice: 16500, resaleHaircut: 0.9 },
  { id: "ebike", pattern: /\be-?bike|electric bike\b/i, category: "vehicles", marketPrice: 900, resaleHaircut: 0.75 },
  { id: "mtb", pattern: /\b(mountain|road) bike\b/i, category: "vehicles", marketPrice: 220, resaleHaircut: 0.7 },
  { id: "iphone", pattern: /\biphone\b/i, category: "electronics", marketPrice: 320, resaleHaircut: 0.8 },
  { id: "macbook", pattern: /\bmacbook\b/i, category: "electronics", marketPrice: 520, resaleHaircut: 0.82 },
  { id: "tv-55", pattern: /\b(55|65)["”]?\s*(tv|television|oled|qled)\b/i, category: "electronics", marketPrice: 380, resaleHaircut: 0.7 },
  { id: "tv", pattern: /\b(tv|television)\b/i, category: "electronics", marketPrice: 220, resaleHaircut: 0.65 },
  { id: "sofa", pattern: /\b(sofa|sectional|couch)\b/i, category: "furniture", marketPrice: 650, resaleHaircut: 0.6 },
  { id: "dining", pattern: /\bdining (table|set)\b/i, category: "furniture", marketPrice: 250, resaleHaircut: 0.62 },
  { id: "mattress", pattern: /\b(mattress|bed in a box)\b/i, category: "furniture", marketPrice: 500, resaleHaircut: 0.55 },
  { id: "crib", pattern: /\bcrib\b/i, category: "furniture", marketPrice: 180, resaleHaircut: 0.5 },
  { id: "washer", pattern: /\b(washer|dryer|laundry (set|pair))\b/i, category: "appliances", marketPrice: 700, resaleHaircut: 0.7 },
  { id: "fridge", pattern: /\b(mini )?fridge|refrigerator\b/i, category: "appliances", marketPrice: 180, resaleHaircut: 0.68 },
  { id: "mixer", pattern: /\b(kitchenaid|stand mixer)\b/i, category: "appliances", marketPrice: 350, resaleHaircut: 0.75 },
  { id: "water-softener", pattern: /\bwater softener\b/i, category: "appliances", marketPrice: 700, resaleHaircut: 0.72 },
  { id: "solar-fan", pattern: /\bsolar (attic )?fan\b/i, category: "solar", marketPrice: 120, resaleHaircut: 0.7 },
  { id: "solar-lights", pattern: /\bsolar\b[\w\s-]{0,24}\b(lights?|lamps?|posts?)\b/i, category: "solar", marketPrice: 45, resaleHaircut: 0.6 },
  { id: "hvac-filter", pattern: /\b(hvac|furnace|air) filters?\b/i, category: "cooling", marketPrice: 80, resaleHaircut: 0.5 },
  { id: "suns-tix", pattern: /\b(suns|cardinals|diamondbacks|coyotes)\b.*\b(ticket|tickets)\b|\btickets?\b.*\b(suns|cardinals|diamondbacks)\b/i, category: "tickets", marketPrice: 110, resaleHaircut: 0.85 },
  { id: "tool-set", pattern: /\b(craftsman|tool (set|chest|box)|mechanic)\b/i, category: "tools", marketPrice: 160, resaleHaircut: 0.75 },
  { id: "generator", pattern: /\bgenerator\b/i, category: "tools", marketPrice: 400, resaleHaircut: 0.78 },
  { id: "mower", pattern: /\b(riding )?mower|lawn tractor\b/i, category: "tools", marketPrice: 800, resaleHaircut: 0.7 },
  { id: "axe", pattern: /\baxe\b/i, category: "tools", marketPrice: 35, resaleHaircut: 0.6 },
];

/** Reject comps that are clearly the wrong class of good (a $60 filter is not a $385k house). */
export function isPlausibleComp(askingPrice: number, marketPrice: number): boolean {
  if (marketPrice >= 5000 && askingPrice < marketPrice * 0.08) return false;
  return true;
}

export function matchMarket(text: string, askingPrice?: number): MarketComp | null {
  for (const comp of MARKET_COMPS) {
    comp.pattern.lastIndex = 0;
    if (!comp.pattern.test(text)) continue;
    if (askingPrice !== undefined && !isPlausibleComp(askingPrice, comp.marketPrice)) continue;
    return comp;
  }
  return null;
}

export function inferCategory(text: string, askingPrice?: number): Category {
  return matchMarket(text, askingPrice)?.category ?? "other";
}
