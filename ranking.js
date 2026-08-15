const clamp = (value, minimum, maximum) => Math.min(Math.max(value, minimum), maximum);

const lensWeights = {
  balanced: { discount: 1, yield: 1, momentum: 1, freshness: 1 },
  cashflow: { discount: 0.62, yield: 1.62, momentum: 0.72, freshness: 0.85 },
  upside: { discount: 1.55, yield: 0.64, momentum: 1.24, freshness: 0.9 },
};

export const formatCurrency = (value, options = {}) =>
  new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 0,
    ...options,
  }).format(value);

export const formatPercent = (value, digits = 1) =>
  new Intl.NumberFormat("en-US", {
    style: "percent",
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  }).format(value);

export function getDiscount(deal) {
  return Math.max(0, (deal.estimatedValue - deal.price) / deal.estimatedValue);
}

export function getNetYield(deal) {
  return Math.max(0, (deal.monthlyRent * 12 - deal.annualExpenses) / deal.price);
}

export function getMonthlyCashFlow(deal) {
  return Math.round((deal.monthlyRent * 12 - deal.annualExpenses) / 12);
}

export function scoreDeal(deal, lens = "balanced") {
  const weights = lensWeights[lens] ?? lensWeights.balanced;
  const discount = getDiscount(deal);
  const netYield = getNetYield(deal);
  const discountPoints = clamp(discount * 280, 0, 40) * weights.discount;
  const yieldPoints = clamp(netYield * 450, 0, 28) * weights.yield;
  const momentumPoints = clamp(deal.marketMomentum, 0, 100) * 0.23 * weights.momentum;
  const freshnessPoints =
    clamp((54 - deal.daysOnMarket) / 6, 0, 8) * weights.freshness;
  const renovationPoints = clamp(deal.renovationReadiness, 0, 100) * 0.045;
  const valueScore = Math.round(
    clamp(
      discountPoints + yieldPoints + momentumPoints + freshnessPoints + renovationPoints,
      1,
      99,
    ),
  );

  return {
    ...deal,
    discount,
    netYield,
    monthlyCashFlow: getMonthlyCashFlow(deal),
    valueScore,
    valueGap: deal.estimatedValue - deal.price,
  };
}

export function rankDeals(deals, lens = "balanced") {
  return deals
    .map((deal, index) => ({ ...scoreDeal(deal, lens), originalIndex: index }))
    .sort(
      (left, right) =>
        right.valueScore - left.valueScore ||
        right.netYield - left.netYield ||
        left.originalIndex - right.originalIndex,
    )
    .map(({ originalIndex, ...deal }) => deal);
}

export function filterDeals(deals, filters = {}) {
  const query = (filters.query ?? "").trim().toLowerCase();
  const maxPrice = Number(filters.maxPrice) || Number.POSITIVE_INFINITY;
  const minBeds = Number(filters.minBeds) || 0;

  return deals.filter((deal) => {
    const matchesMarket = !filters.market || filters.market === "All Arizona" || deal.market === filters.market;
    const matchesType = !filters.type || filters.type === "All homes" || deal.type === filters.type;
    const matchesPrice = deal.price <= maxPrice;
    const matchesBeds = deal.beds >= minBeds;
    const searchable = `${deal.title} ${deal.neighborhood} ${deal.city} ${deal.market}`.toLowerCase();
    const matchesQuery = !query || searchable.includes(query);

    return matchesMarket && matchesType && matchesPrice && matchesBeds && matchesQuery;
  });
}
