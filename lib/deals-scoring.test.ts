import { calculateValueScore } from '@/lib/scoring';
import { getFilteredAndRankedDeals, computeDealStats, ARIZONA_DEALS } from '@/lib/deals';
import { ArizonaDealAgentEngine } from '@/lib/agent-engine';

describe('Arizona Deal Scoring Algorithm', () => {
  test('calculates accurate discount and ROI scores for real estate foreclosure', () => {
    const result = calculateValueScore({
      category: 'real-estate',
      price: 450000,
      originalPrice: 600000,
      marketAveragePrice: 590000,
      conditionRating: 4.8,
      estimatedResaleValue: 585000,
      daysOnMarketOrExpiresInDays: 4,
      verified: true,
    });

    expect(result.compositeScore).toBeGreaterThanOrEqual(75);
    expect(result.savingsDollars).toBe(150000);
    expect(result.savingsPercentage).toBe(25);
    expect(result.valueTier).toBeDefined();
    expect(result.reasoning.length).toBeGreaterThan(0);
  });

  test('rewards deep discounts with Exceptional tier rating', () => {
    const result = calculateValueScore({
      category: 'travel-resorts',
      price: 500,
      originalPrice: 1500,
      conditionRating: 5.0,
      daysOnMarketOrExpiresInDays: 2,
      verified: true,
    });

    expect(result.savingsPercentage).toBe(67);
    expect(result.compositeScore).toBeGreaterThanOrEqual(85);
    expect(result.valueTier).toBe('Exceptional');
  });

  test('handles edge cases where deal price equals original price gracefully', () => {
    const result = calculateValueScore({
      category: 'electronics-goods',
      price: 1000,
      originalPrice: 1000,
      conditionRating: 3.0,
      verified: false,
    });

    expect(result.savingsDollars).toBe(0);
    expect(result.savingsPercentage).toBe(0);
    expect(result.compositeScore).toBeLessThan(60);
    expect(result.valueTier).toBe('Fair');
  });

  test('prioritizes vehicles and goods with fast resale margins', () => {
    const veh = calculateValueScore({
      category: 'vehicles',
      price: 25000,
      originalPrice: 38000,
      estimatedResaleValue: 35000,
      conditionRating: 4.9,
      verified: true,
    });

    expect(veh.roiScore).toBeGreaterThanOrEqual(70);
    expect(veh.estimatedRoiPercentage).toBeGreaterThanOrEqual(30);
    expect(veh.compositeScore).toBeGreaterThanOrEqual(80);
  });
});

describe('Deals Ranking & Filtering Engine', () => {
  test('ranks deals by composite score descending by default', () => {
    const ranked = getFilteredAndRankedDeals(ARIZONA_DEALS, { sortBy: 'score' });
    expect(ranked.length).toBeGreaterThan(0);

    for (let i = 0; i < ranked.length - 1; i++) {
      expect(ranked[i].valueScore.compositeScore).toBeGreaterThanOrEqual(
        ranked[i + 1].valueScore.compositeScore
      );
    }
  });

  test('filters deals accurately by Arizona region', () => {
    const scottsdaleDeals = getFilteredAndRankedDeals(ARIZONA_DEALS, {
      region: 'Scottsdale & East Valley',
    });

    expect(scottsdaleDeals.length).toBeGreaterThan(0);
    scottsdaleDeals.forEach((deal) => {
      expect(deal.location.region).toBe('Scottsdale & East Valley');
    });
  });

  test('filters deals accurately by category', () => {
    const vehicles = getFilteredAndRankedDeals(ARIZONA_DEALS, {
      category: 'vehicles',
    });

    expect(vehicles.length).toBeGreaterThan(0);
    vehicles.forEach((deal) => {
      expect(deal.category).toBe('vehicles');
    });
  });

  test('filters deals accurately by keyword search', () => {
    const sedonaDeals = getFilteredAndRankedDeals(ARIZONA_DEALS, {
      search: 'Sedona',
    });

    expect(sedonaDeals.length).toBeGreaterThan(0);
    sedonaDeals.forEach((deal) => {
      const match =
        deal.title.includes('Sedona') ||
        deal.description.includes('Sedona') ||
        deal.location.city.includes('Sedona') ||
        deal.location.region.includes('Sedona') ||
        deal.tags.some((t) => t.includes('Sedona'));
      expect(match).toBe(true);
    });
  });

  test('computes aggregate deal statistics correctly', () => {
    const stats = computeDealStats(ARIZONA_DEALS);
    expect(stats.totalDeals).toBe(ARIZONA_DEALS.length);
    expect(stats.totalPotentialSavings).toBeGreaterThan(0);
    expect(stats.averageDiscountPct).toBeGreaterThan(0);
    expect(stats.topCategory).toBeDefined();
    expect(stats.topRegion).toBeDefined();
  });
});

describe('Arizona Deal Agent Engine', () => {
  const engine = new ArizonaDealAgentEngine();

  test('ingests and normalizes custom deal submissions', () => {
    const custom = engine.analyzeAndIngestDeal({
      title: 'Tucson Solar Home Foreclosure',
      description: '3-bed home with active net-metered solar in Tucson.',
      category: 'real-estate',
      source: 'Tucson Trustee Auction',
      price: 275000,
      originalPrice: 380000,
      city: 'Tucson',
      region: 'Tucson & Southern AZ',
      conditionRating: 4.5,
    });

    expect(custom.id).toContain('az-custom-');
    expect(custom.valueScore.compositeScore).toBeGreaterThan(0);
    expect(custom.location.city).toBe('Tucson');
  });

  test('generates dynamic live market query results', () => {
    const golfDeals = engine.generateLiveMarketDeals('golf resort');
    expect(golfDeals.length).toBeGreaterThan(0);
    expect(golfDeals[0].title).toContain('Golf');
  });
});
