import { deals } from '../data/deals'
import { getDiscountPercent, rankDeals, scoreDeal } from './scoring'

describe('deal scoring', () => {
  it('calculates the discount from market value', () => {
    expect(getDiscountPercent(deals[0])).toBeCloseTo(17.55, 1)
  })

  it('keeps every factor and total inside the 0–100 range', () => {
    for (const deal of deals) {
      for (const strategy of [
        'balanced',
        'cash-flow',
        'appreciation',
        'affordable',
      ] as const) {
        const score = scoreDeal(deal, strategy)
        expect(Object.values(score).every((value) => value >= 0)).toBe(true)
        expect(Object.values(score).every((value) => value <= 100)).toBe(true)
      }
    }
  })

  it('ranks the strongest cash-flow property first for that strategy', () => {
    expect(rankDeals(deals, 'cash-flow')[0].id).toBe('az-008')
  })

  it('ranks the lowest-entry property first for affordability', () => {
    expect(rankDeals(deals, 'affordable')[0].id).toBe('az-003')
  })

  it('returns scores in descending order', () => {
    const ranked = rankDeals(deals, 'balanced')
    const scores = ranked.map((deal) => scoreDeal(deal, 'balanced').total)

    expect(scores).toEqual([...scores].sort((a, b) => b - a))
  })
})
