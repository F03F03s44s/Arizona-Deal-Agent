import assert from "node:assert/strict";
import test from "node:test";

import { deals } from "../deals-data.js";
import {
  filterDeals,
  getMonthlyCashFlow,
  rankDeals,
  scoreDeal,
} from "../ranking.js";

test("rankDeals returns a descending, bounded value-score ranking", () => {
  const ranked = rankDeals(deals);

  assert.equal(ranked.length, deals.length);
  assert.ok(ranked.every((deal) => deal.valueScore >= 1 && deal.valueScore <= 99));
  assert.ok(
    ranked.every(
      (deal, index) => index === 0 || ranked[index - 1].valueScore >= deal.valueScore,
    ),
  );
});

test("cash flow and upside lenses prioritize their intended tradeoffs", () => {
  const tradeoffDeals = [
    {
      id: "upside",
      price: 800000,
      estimatedValue: 1000000,
      monthlyRent: 2100,
      annualExpenses: 4800,
      marketMomentum: 60,
      renovationReadiness: 100,
      daysOnMarket: 12,
    },
    {
      id: "cashflow",
      price: 970000,
      estimatedValue: 1000000,
      monthlyRent: 9700,
      annualExpenses: 0,
      marketMomentum: 60,
      renovationReadiness: 100,
      daysOnMarket: 12,
    },
  ];

  assert.equal(rankDeals(tradeoffDeals, "cashflow")[0].id, "cashflow");
  assert.equal(rankDeals(tradeoffDeals, "upside")[0].id, "upside");
});

test("filters combine market, property, price, bed count, and query", () => {
  const matching = filterDeals(deals, {
    market: "Phoenix",
    type: "Single family",
    maxPrice: "500000",
    minBeds: "3",
    query: "historic",
  });

  assert.deepEqual(matching.map((deal) => deal.id), ["garfield-bungalow"]);
});

test("scoreDeal exposes net operating cash flow for each deal", () => {
  const deal = deals.find((item) => item.id === "mesa-midcentury");
  const scored = scoreDeal(deal);

  assert.equal(getMonthlyCashFlow(deal), 2620);
  assert.equal(scored.monthlyCashFlow, 2620);
  assert.ok(scored.valueGap > 0);
  assert.ok(scored.netYield > 0);
});
