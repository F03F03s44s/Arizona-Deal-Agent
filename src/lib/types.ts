export const CATEGORIES = [
  "cooling",
  "outdoor",
  "vehicles",
  "electronics",
  "furniture",
  "housing",
  "appliances",
  "tickets",
  "tools",
  "solar",
  "other",
] as const;

export type Category = (typeof CATEGORIES)[number];

export const CITIES = [
  "Phoenix",
  "Tucson",
  "Mesa",
  "Chandler",
  "Scottsdale",
  "Gilbert",
  "Glendale",
  "Tempe",
  "Peoria",
  "Surprise",
  "Flagstaff",
  "Yuma",
  "Statewide",
] as const;

export type City = (typeof CITIES)[number];

export type Condition = "new" | "like-new" | "good" | "fair" | "unknown";
export type Pricing = "sale" | "monthly";
export type DealKind = "local" | "housing" | "national";
export type Recommendation = "buy" | "watch" | "skip";

export type Deal = {
  id: string;
  title: string;
  description: string;
  category: Category;
  city: City;
  askingPrice: number;
  marketPrice: number | null;
  estimatedResale: number | null;
  monthlyRent: number | null;
  condition: Condition;
  pricing: Pricing;
  kind: DealKind;
  source: string;
  sourceLabel: string;
  url: string;
  postedAt: string;
  tags: string[];
  arizonaFit: number;
};

export type ScoreBreakdown = {
  priceAdvantage: number;
  affordability: number;
  profitPotential: number;
  recency: number;
  arizonaFit: number;
};

export type RankedDeal = Deal & {
  rank: number;
  valueScore: number;
  savings: number;
  savingsPct: number;
  profit: number;
  capRate: number | null;
  scores: ScoreBreakdown;
  recommendation: Recommendation;
  reasons: string[];
};

export type DealFilters = {
  city?: string;
  category?: string;
  maxPrice?: number;
  minScore?: number;
  recommendation?: Recommendation | "any";
  q?: string;
};

export type SourceStatus = {
  id: string;
  label: string;
  ok: boolean;
  count: number;
  error?: string;
};

export type PipelineResult = {
  deals: RankedDeal[];
  scanned: number;
  ranked: number;
  generatedAt: string;
  sources: SourceStatus[];
};
