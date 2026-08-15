import type { Deal, ScoreBreakdown, Strategy } from '../types'

type ScoreFactor = keyof Omit<ScoreBreakdown, 'total'>

const weights: Record<Strategy, Record<ScoreFactor, number>> = {
  balanced: {
    affordability: 0.18,
    cashFlow: 0.22,
    yield: 0.24,
    discount: 0.24,
    market: 0.12,
  },
  'cash-flow': {
    affordability: 0.1,
    cashFlow: 0.35,
    yield: 0.3,
    discount: 0.15,
    market: 0.1,
  },
  appreciation: {
    affordability: 0.1,
    cashFlow: 0.1,
    yield: 0.15,
    discount: 0.25,
    market: 0.4,
  },
  affordable: {
    affordability: 0.38,
    cashFlow: 0.18,
    yield: 0.14,
    discount: 0.22,
    market: 0.08,
  },
}

const clamp = (value: number, minimum = 0, maximum = 100) =>
  Math.min(Math.max(value, minimum), maximum)

export const getDiscountPercent = (deal: Deal) =>
  ((deal.marketValue - deal.price) / deal.marketValue) * 100

export function scoreDeal(deal: Deal, strategy: Strategy): ScoreBreakdown {
  const breakdown = {
    affordability: clamp(100 - ((deal.price - 180000) / 320000) * 100),
    cashFlow: clamp(((deal.monthlyCashFlow + 100) / 950) * 100),
    yield: clamp(((deal.capRate - 4) / 5) * 100),
    discount: clamp((getDiscountPercent(deal) / 22) * 100),
    market: clamp(((deal.annualGrowth - 3) / 5.5) * 100),
  }

  const total = Object.entries(weights[strategy]).reduce(
    (score, [factor, weight]) =>
      score + breakdown[factor as ScoreFactor] * weight,
    0,
  )

  return {
    total: Math.round(total),
    affordability: Math.round(breakdown.affordability),
    cashFlow: Math.round(breakdown.cashFlow),
    yield: Math.round(breakdown.yield),
    discount: Math.round(breakdown.discount),
    market: Math.round(breakdown.market),
  }
}

export function rankDeals(list: Deal[], strategy: Strategy) {
  return [...list].sort(
    (first, second) =>
      scoreDeal(second, strategy).total - scoreDeal(first, strategy).total,
  )
}

export function getScoreLabel(score: number) {
  if (score >= 80) return 'Exceptional'
  if (score >= 70) return 'Strong value'
  if (score >= 60) return 'Worth a look'
  return 'Watchlist'
}

export function formatCurrency(value: number, compact = false) {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    maximumFractionDigits: 0,
    notation: compact ? 'compact' : 'standard',
  }).format(value)
}
