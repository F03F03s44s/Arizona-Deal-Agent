import type { Deal, RankedDeal, Recommendation, ScoreBreakdown } from "./types";

export const WEIGHTS = {
  priceAdvantage: 0.36,
  affordability: 0.2,
  profitPotential: 0.24,
  recency: 0.1,
  arizonaFit: 0.1,
} as const;

export const BUY_SCORE = 70;
export const WATCH_SCORE = 50;
export const BUY_SAVINGS_PCT = 0.22;

function clamp(value: number, min: number, max: number): number {
  return Math.min(max, Math.max(min, value));
}

function hoursSince(iso: string, now: number): number {
  const then = new Date(iso).getTime();
  if (Number.isNaN(then)) return 72;
  return Math.max(0, (now - then) / 3_600_000);
}

export function priceAdvantageScore(asking: number, market: number | null): number {
  if (!market || market <= 0) return 32;
  const pct = (market - asking) / market;
  if (pct <= -0.15) return clamp(20 + pct * 80, 0, 20);
  return clamp(pct * 125, 0, 100);
}

export function affordabilityScore(deal: Deal): number {
  const price = deal.askingPrice;
  if (deal.category === "housing" && deal.pricing === "sale") {
    return clamp(100 * (1 - price / 520_000), 8, 100);
  }
  if (deal.pricing === "monthly") {
    return clamp(100 * (1 - price / 2_200), 8, 100);
  }
  return clamp(108 - Math.log10(price + 12) * 24, 8, 100);
}

export function profitPotentialScore(deal: Deal): number {
  if (deal.category === "housing" && deal.monthlyRent && deal.askingPrice > 0) {
    const cap = (deal.monthlyRent * 12 * 0.62) / deal.askingPrice;
    return clamp(cap * 780, 0, 100);
  }
  const resale = deal.estimatedResale ?? (deal.marketPrice ? deal.marketPrice * 0.82 : null);
  if (!resale) return 28;
  const profit = resale - deal.askingPrice;
  const roi = deal.askingPrice > 0 ? profit / deal.askingPrice : 0;
  const base = clamp(roi * 70, -20, 80);
  return clamp(base + (profit > 0 ? 18 : 0), 0, 100);
}

export function recencyScore(postedAt: string, now: number): number {
  const ageHours = hoursSince(postedAt, now);
  return clamp(100 * Math.exp(-ageHours / 160), 6, 100);
}

export function capRate(deal: Deal): number | null {
  if (!deal.monthlyRent || deal.askingPrice <= 0 || deal.pricing !== "sale") return null;
  return (deal.monthlyRent * 12 * 0.62) / deal.askingPrice;
}

export function savingsFor(deal: Deal): { savings: number; savingsPct: number } {
  if (!deal.marketPrice || deal.marketPrice <= 0) {
    return { savings: 0, savingsPct: 0 };
  }
  const savings = deal.marketPrice - deal.askingPrice;
  return { savings, savingsPct: savings / deal.marketPrice };
}

export function scoreBreakdown(deal: Deal, now = Date.now()): ScoreBreakdown {
  return {
    priceAdvantage: priceAdvantageScore(deal.askingPrice, deal.marketPrice),
    affordability: affordabilityScore(deal),
    profitPotential: profitPotentialScore(deal),
    recency: recencyScore(deal.postedAt, now),
    arizonaFit: clamp(deal.arizonaFit, 0, 100),
  };
}

export function combineScore(scores: ScoreBreakdown, condition: Deal["condition"]): number {
  const raw =
    WEIGHTS.priceAdvantage * scores.priceAdvantage +
    WEIGHTS.affordability * scores.affordability +
    WEIGHTS.profitPotential * scores.profitPotential +
    WEIGHTS.recency * scores.recency +
    WEIGHTS.arizonaFit * scores.arizonaFit;

  const conditionFactor: Record<Deal["condition"], number> = {
    new: 1,
    "like-new": 0.98,
    good: 0.94,
    fair: 0.86,
    unknown: 0.92,
  };

  return clamp(raw * conditionFactor[condition], 0, 100);
}

export function recommend(valueScore: number, savingsPct: number, profit: number): Recommendation {
  if (valueScore >= BUY_SCORE && (savingsPct >= BUY_SAVINGS_PCT || profit > 0)) return "buy";
  if (valueScore >= WATCH_SCORE) return "watch";
  return "skip";
}

export function explain(deal: Deal, scores: ScoreBreakdown, savingsPct: number, profit: number): string[] {
  const reasons: string[] = [];
  if (deal.marketPrice && savingsPct >= 0.2) {
    reasons.push(
      `${Math.round(savingsPct * 100)}% under the typical Arizona ${deal.category} comp of ${formatUsd(deal.marketPrice)}.`,
    );
  } else if (deal.marketPrice && savingsPct < 0) {
    reasons.push(`Asking is above the ${formatUsd(deal.marketPrice)} market comp — weak value.`);
  } else if (!deal.marketPrice) {
    reasons.push("No tight market comp; scored conservatively.");
  }

  if (deal.category === "housing" && deal.monthlyRent && deal.askingPrice > 0) {
    const cap = capRate(deal);
    if (cap) {
      reasons.push(`Estimated cap rate ${ (cap * 100).toFixed(1) }% on ${formatUsd(deal.monthlyRent)}/mo rent.`);
    }
  } else if (profit > 40) {
    reasons.push(`Estimated flip room of ${formatUsd(profit)} after a realistic resale haircut.`);
  }

  if (scores.affordability >= 70) {
    reasons.push("Low cash outlay — easier to act on today.");
  }
  if (scores.recency >= 70) {
    reasons.push("Fresh listing — less likely to be picked over.");
  }
  if (deal.arizonaFit >= 70) {
    reasons.push(`Strong Arizona fit in ${deal.city}.`);
  } else if (deal.kind === "national") {
    reasons.push("National deal that still ships or applies in Arizona.");
  }

  return reasons.slice(0, 3);
}

function formatUsd(value: number): string {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: value >= 1000 ? 0 : 2,
  }).format(value);
}

export function rankDeals(deals: Deal[], now = Date.now()): RankedDeal[] {
  const ranked = deals
    .filter((deal) => Number.isFinite(deal.askingPrice) && deal.askingPrice > 0)
    .map((deal) => {
      const scores = scoreBreakdown(deal, now);
      const valueScore = combineScore(scores, deal.condition);
      const { savings, savingsPct } = savingsFor(deal);
      const resale = deal.estimatedResale ?? (deal.marketPrice ? deal.marketPrice * 0.82 : 0);
      const profit = deal.category === "housing" ? savings : resale - deal.askingPrice;
      const recommendation = recommend(valueScore, savingsPct, profit);
      return {
        ...deal,
        rank: 0,
        valueScore: Math.round(valueScore * 10) / 10,
        savings: Math.round(savings),
        savingsPct,
        profit: Math.round(profit),
        capRate: capRate(deal),
        scores,
        recommendation,
        reasons: explain(deal, scores, savingsPct, profit),
      };
    })
    .sort((a, b) => {
      if (b.valueScore !== a.valueScore) return b.valueScore - a.valueScore;
      if (b.savings !== a.savings) return b.savings - a.savings;
      return a.askingPrice - b.askingPrice;
    });

  return ranked.map((deal, index) => ({ ...deal, rank: index + 1 }));
}
