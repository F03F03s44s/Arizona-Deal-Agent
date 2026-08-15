export type DealCategory =
  | 'real-estate'
  | 'vehicles'
  | 'travel-resorts'
  | 'experiences-dining'
  | 'electronics-goods';

export type ArizonaRegion =
  | 'Phoenix Metro'
  | 'Scottsdale & East Valley'
  | 'Tucson & Southern AZ'
  | 'Flagstaff & Northern AZ'
  | 'Sedona & Verde Valley'
  | 'Yuma & Western AZ'
  | 'Statewide / Online';

export type ValueTier = 'Exceptional' | 'Great' | 'Good' | 'Fair';

export interface DealLocation {
  city: string;
  region: ArizonaRegion;
  zipCode?: string;
  lat?: number;
  lng?: number;
  address?: string;
}

export interface ValueScoreBreakdown {
  discountScore: number;       // 0-100: How deep the discount is vs market
  roiScore: number;             // 0-100: Return on investment / resale / yield
  historicalScore: number;      // 0-100: Price compared to 30/90-day AZ average
  urgencyScore: number;         // 0-100: Time-sensitivity or stock scarcity
  qualityScore: number;         // 0-100: Item condition, brand, rating, or neighborhood quality
  liquidityScore: number;       // 0-100: Ease of resale or utility
  compositeScore: number;       // 0-100: Weighted total best-value rating
  valueTier: ValueTier;
  savingsDollars: number;
  savingsPercentage: number;
  estimatedResaleValue?: number;
  estimatedRoiPercentage?: number;
  reasoning: string[];
}

export interface Deal {
  id: string;
  title: string;
  description: string;
  category: DealCategory;
  source: string;              // e.g. 'AZ MLS Foreclosures', 'Craigslist Phoenix', 'BringATrailer AZ', 'Scottsdale Resort Deals', 'OfferUp Valley'
  sourceUrl?: string;
  price: number;
  originalPrice: number;
  currency: string;
  location: DealLocation;
  images: string[];
  tags: string[];
  features?: Record<string, string | number | boolean>;
  postedAt: string;
  expiresAt?: string;
  verified: boolean;
  valueScore: ValueScoreBreakdown;
}

export interface DealFilterOptions {
  category?: DealCategory | 'all';
  region?: ArizonaRegion | 'all';
  search?: string;
  minPrice?: number;
  maxPrice?: number;
  minScore?: number;
  valueTier?: ValueTier | 'all';
  sortBy?: 'score' | 'savings_desc' | 'savings_pct' | 'price_asc' | 'price_desc' | 'newest';
}

export interface DealStats {
  totalDeals: number;
  averageDiscountPct: number;
  totalPotentialSavings: number;
  topCategory: DealCategory;
  topRegion: ArizonaRegion;
  dealCountsByCategory: Record<DealCategory, number>;
  dealCountsByRegion: Record<ArizonaRegion, number>;
}
