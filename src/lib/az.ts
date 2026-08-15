import type { City } from "./types";

export const ARIZONA_CITY_ALIASES: Record<string, City> = {
  phoenix: "Phoenix",
  phx: "Phoenix",
  ahwatukee: "Phoenix",
  "arcadia": "Phoenix",
  maryvale: "Phoenix",
  "downtown phoenix": "Phoenix",
  tucson: "Tucson",
  "oro valley": "Tucson",
  "marana": "Tucson",
  mesa: "Mesa",
  chandler: "Chandler",
  scottsdale: "Scottsdale",
  gilbert: "Gilbert",
  glendale: "Glendale",
  tempe: "Tempe",
  peoria: "Peoria",
  surprise: "Surprise",
  flagstaff: "Flagstaff",
  yuma: "Yuma",
  arizona: "Statewide",
  az: "Statewide",
  "valley of the sun": "Phoenix",
};

const CITY_PATTERN = new RegExp(
  `\\b(${Object.keys(ARIZONA_CITY_ALIASES).sort((a, b) => b.length - a.length).join("|")})\\b`,
  "i",
);

/** Items that save money or stay useful in Arizona heat, sun, and hard water. */
export const CLIMATE_PATTERNS: RegExp[] = [
  /\b(a\/?c|air ?condition(?:er|ing)|portable ac|window ac|mini[- ]?split)\b/i,
  /\b(swamp cooler|evaporative cooler|cooler)\b/i,
  /\b(patio|umbrella|canopy|shade|sun sail|gazebo|pergola)\b/i,
  /\b(pool|pool pump|pool filter|mister|misting)\b/i,
  /\b(solar|attic fan|sunshade|windshield shade)\b/i,
  /\b(ceiling fan|box fan|tower fan|outdoor fan)\b/i,
  /\b(water softener|whole[- ]house filter)\b/i,
  /\b(rv|trailer|pickup|f-?150|tacoma)\b/i,
];

export function detectCity(text: string): City | null {
  const match = text.match(CITY_PATTERN);
  if (!match) return null;
  return ARIZONA_CITY_ALIASES[match[1].toLowerCase()] ?? null;
}

export function climateRelevance(text: string): number {
  let hits = 0;
  for (const pattern of CLIMATE_PATTERNS) {
    if (pattern.test(text)) hits += 1;
  }
  if (hits === 0) return 0;
  return Math.min(100, 45 + hits * 18);
}

export function arizonaFit(text: string): number {
  const city = detectCity(text);
  const climate = climateRelevance(text);
  const explicitAz = /\barizona\b|\b\baz\b/i.test(text);
  let score = 18;
  if (city && city !== "Statewide") score += 55;
  else if (city === "Statewide" || explicitAz) score += 40;
  score += climate * 0.35;
  return Math.max(0, Math.min(100, Math.round(score)));
}

export function isArizonaUseful(text: string, minFit = 28): boolean {
  return arizonaFit(text) >= minFit || climateRelevance(text) >= 45;
}
