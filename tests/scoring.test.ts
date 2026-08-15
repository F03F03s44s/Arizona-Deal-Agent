import { describe, expect, it } from "vitest";
import { loadCatalog } from "@/lib/sources/catalog";
import {
  BUY_SCORE,
  affordabilityScore,
  combineScore,
  priceAdvantageScore,
  rankDeals,
  recommend,
} from "@/lib/scoring";
import type { Deal } from "@/lib/types";

const NOW = Date.parse("2026-08-15T12:00:00.000Z");

function deal(overrides: Partial<Deal> & Pick<Deal, "id" | "title" | "askingPrice">): Deal {
  return {
    description: "",
    category: "other",
    city: "Phoenix",
    marketPrice: null,
    estimatedResale: null,
    monthlyRent: null,
    condition: "good",
    pricing: "sale",
    kind: "local",
    source: "test",
    sourceLabel: "test",
    url: "#",
    postedAt: new Date(NOW - 4 * 3_600_000).toISOString(),
    tags: [],
    arizonaFit: 80,
    ...overrides,
  };
}

describe("priceAdvantageScore", () => {
  it("rewards deep discounts vs market", () => {
    expect(priceAdvantageScore(90, 280)).toBeGreaterThan(priceAdvantageScore(250, 280));
    expect(priceAdvantageScore(90, 280)).toBeGreaterThan(80);
  });

  it("penalizes asking above market", () => {
    expect(priceAdvantageScore(220, 80)).toBeLessThan(20);
  });
});

describe("affordabilityScore", () => {
  it("scores cheap marketplace items higher than expensive ones", () => {
    const cheap = deal({ id: "c", title: "fan", askingPrice: 35, category: "cooling" });
    const spendy = deal({ id: "s", title: "truck", askingPrice: 8900, category: "vehicles" });
    expect(affordabilityScore(cheap)).toBeGreaterThan(affordabilityScore(spendy));
  });

  it("does not zero-out a discounted Arizona house", () => {
    const house = deal({
      id: "h",
      title: "duplex",
      askingPrice: 219000,
      category: "housing",
      pricing: "sale",
    });
    expect(affordabilityScore(house)).toBeGreaterThan(40);
  });
});

describe("rankDeals", () => {
  it("ranks the Mesa AC above the overpriced lamp", () => {
    const ranked = rankDeals(loadCatalog(NOW), NOW);
    const ac = ranked.find((item) => item.id.endsWith("mesa-window-ac"));
    const lamp = ranked.find((item) => item.id.endsWith("scottsdale-lamp"));
    expect(ac).toBeDefined();
    expect(lamp).toBeDefined();
    expect(ac!.rank).toBeLessThan(lamp!.rank);
    expect(ac!.valueScore).toBeGreaterThan(lamp!.valueScore);
  });

  it("puts the Tucson duplex ahead of the at-comp Mesa townhome", () => {
    const ranked = rankDeals(loadCatalog(NOW), NOW);
    const duplex = ranked.find((item) => item.id.endsWith("tucson-duplex"));
    const townhome = ranked.find((item) => item.id.endsWith("mesa-townhome"));
    expect(duplex!.valueScore).toBeGreaterThan(townhome!.valueScore);
    expect(duplex!.capRate).not.toBeNull();
    expect(duplex!.capRate!).toBeGreaterThan(townhome!.capRate ?? 0);
  });

  it("assigns buy to a deep local bargain", () => {
    const ranked = rankDeals(loadCatalog(NOW), NOW);
    const dining = ranked.find((item) => item.id.endsWith("mesa-dining"));
    expect(dining!.recommendation).toBe("buy");
    expect(dining!.valueScore).toBeGreaterThanOrEqual(BUY_SCORE);
  });

  it("assigns skip to thin-margin socks", () => {
    const ranked = rankDeals(loadCatalog(NOW), NOW);
    const socks = ranked.find((item) => item.id.endsWith("phoenix-socks"));
    expect(socks!.recommendation).toBe("skip");
  });

  it("sorts by value score then savings", () => {
    const ranked = rankDeals(loadCatalog(NOW), NOW);
    for (let i = 1; i < ranked.length; i += 1) {
      expect(ranked[i - 1].valueScore).toBeGreaterThanOrEqual(ranked[i].valueScore);
    }
    expect(ranked[0].rank).toBe(1);
  });
});

describe("recommend", () => {
  it("requires both score and value to buy", () => {
    expect(recommend(80, 0.3, 50)).toBe("buy");
    expect(recommend(80, 0.05, -10)).toBe("watch");
    expect(recommend(40, 0.5, 20)).toBe("skip");
  });
});

describe("combineScore", () => {
  it("stays within 0-100", () => {
    const score = combineScore(
      {
        priceAdvantage: 100,
        affordability: 100,
        profitPotential: 100,
        recency: 100,
        arizonaFit: 100,
      },
      "new",
    );
    expect(score).toBe(100);
  });
});
