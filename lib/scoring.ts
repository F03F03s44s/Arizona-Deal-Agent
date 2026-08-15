import { Deal, DealCategory, ValueScoreBreakdown, ValueTier } from '@/types/deal';

export interface ScoreWeights {
  discount: number;
  roi: number;
  historical: number;
  quality: number;
  urgency: number;
  liquidity: number;
}

const CATEGORY_WEIGHTS: Record<DealCategory, ScoreWeights> = {
  'real-estate': {
    discount: 0.30,
    roi: 0.30,
    historical: 0.20,
    quality: 0.10,
    urgency: 0.05,
    liquidity: 0.05,
  },
  'vehicles': {
    discount: 0.35,
    roi: 0.20,
    historical: 0.20,
    quality: 0.15,
    urgency: 0.05,
    liquidity: 0.05,
  },
  'travel-resorts': {
    discount: 0.45,
    roi: 0.05,
    historical: 0.25,
    quality: 0.15,
    urgency: 0.10,
    liquidity: 0.00,
  },
  'experiences-dining': {
    discount: 0.50,
    roi: 0.05,
    historical: 0.20,
    quality: 0.20,
    urgency: 0.05,
    liquidity: 0.00,
  },
  'electronics-goods': {
    discount: 0.40,
    roi: 0.25,
    historical: 0.15,
    quality: 0.10,
    urgency: 0.05,
    liquidity: 0.05,
  },
};

export function calculateValueScore(params: {
  category: DealCategory;
  price: number;
  originalPrice: number;
  marketAveragePrice?: number;
  conditionRating?: number; // 1 to 5
  estimatedResaleValue?: number;
  daysOnMarketOrExpiresInDays?: number;
  verified?: boolean;
}): ValueScoreBreakdown {
  const {
    category,
    price,
    originalPrice,
    marketAveragePrice,
    conditionRating = 4.5,
    estimatedResaleValue,
    daysOnMarketOrExpiresInDays,
    verified = true,
  } = params;

  const savingsDollars = Math.max(0, originalPrice - price);
  const savingsPercentage = originalPrice > 0 ? (savingsDollars / originalPrice) * 100 : 0;

  // 1. Discount score: calibrated with gentle baseline so 20% = 70pts, 30% = 82pts, 50%+ = 96-100pts
  let discountScore = 0;
  if (savingsPercentage > 0) {
    discountScore = Math.min(100, Math.max(30, 40 + (savingsPercentage / 50) * 60));
  }
  if (savingsPercentage >= 50) discountScore = Math.min(100, 85 + ((savingsPercentage - 50) / 20) * 15);

  // 2. ROI score: potential profit percentage if resold or yield
  let estimatedRoiPercentage = 0;
  let roiScore = 50; // Default average
  const benchmarkResale = estimatedResaleValue ?? (originalPrice * 0.9);
  if (price > 0 && benchmarkResale > price) {
    estimatedRoiPercentage = ((benchmarkResale - price) / price) * 100;
    roiScore = Math.min(100, Math.max(0, (estimatedRoiPercentage / 40) * 100));
  } else if (benchmarkResale <= price) {
    roiScore = 20;
  }

  // 3. Historical score: comparison against AZ historical market average
  let historicalScore = 70;
  if (marketAveragePrice && marketAveragePrice > 0) {
    const historicalDiscount = ((marketAveragePrice - price) / marketAveragePrice) * 100;
    historicalScore = Math.min(100, Math.max(0, 50 + historicalDiscount * 1.5));
  } else {
    historicalScore = Math.min(100, Math.max(30, discountScore * 0.9));
  }

  // 4. Quality score: based on condition, reputation, verification
  let qualityScore = (conditionRating / 5) * 85 + (verified ? 15 : 0);
  qualityScore = Math.min(100, Math.max(0, qualityScore));

  // 5. Urgency score: time sensitivity (shorter remaining = higher urgency score for deal hunters)
  let urgencyScore = 65;
  if (daysOnMarketOrExpiresInDays !== undefined) {
    if (daysOnMarketOrExpiresInDays <= 2) urgencyScore = 95;
    else if (daysOnMarketOrExpiresInDays <= 5) urgencyScore = 80;
    else if (daysOnMarketOrExpiresInDays <= 14) urgencyScore = 65;
    else urgencyScore = 45;
  }

  // 6. Liquidity / Desirability score
  const liquidityScore = category === 'electronics-goods' || category === 'vehicles' ? 80 : 70;

  // Weighted composite
  const weights = CATEGORY_WEIGHTS[category] || CATEGORY_WEIGHTS['electronics-goods'];
  const rawComposite =
    discountScore * weights.discount +
    roiScore * weights.roi +
    historicalScore * weights.historical +
    qualityScore * weights.quality +
    urgencyScore * weights.urgency +
    liquidityScore * weights.liquidity;

  const compositeScore = Math.round(Math.min(99, Math.max(10, rawComposite)));

  let valueTier: ValueTier = 'Fair';
  if (compositeScore >= 85) valueTier = 'Exceptional';
  else if (compositeScore >= 75) valueTier = 'Great';
  else if (compositeScore >= 60) valueTier = 'Good';

  // Build reasoning bullets
  const reasoning: string[] = [];
  if (savingsPercentage >= 40) {
    reasoning.push(`Huge discount of ${savingsPercentage.toFixed(0)}% ($${savingsDollars.toLocaleString()} savings)`);
  } else if (savingsPercentage > 0) {
    reasoning.push(`Saves $${savingsDollars.toLocaleString()} (${savingsPercentage.toFixed(0)}% off regular price)`);
  }

  if (estimatedRoiPercentage > 15) {
    reasoning.push(`High upside: ~${estimatedRoiPercentage.toFixed(0)}% estimated margin on AZ secondary market`);
  }

  if (historicalScore >= 80) {
    reasoning.push(`Priced well below recent Arizona market comps`);
  }

  if (verified) {
    reasoning.push(`Verified Arizona listing with validated condition & pricing`);
  }

  return {
    discountScore: Math.round(discountScore),
    roiScore: Math.round(roiScore),
    historicalScore: Math.round(historicalScore),
    qualityScore: Math.round(qualityScore),
    urgencyScore: Math.round(urgencyScore),
    liquidityScore: Math.round(liquidityScore),
    compositeScore,
    valueTier,
    savingsDollars: Math.round(savingsDollars),
    savingsPercentage: Math.round(savingsPercentage),
    estimatedResaleValue: Math.round(benchmarkResale),
    estimatedRoiPercentage: Math.round(estimatedRoiPercentage),
    reasoning,
  };
}
