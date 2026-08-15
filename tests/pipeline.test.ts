import { describe, expect, it } from "vitest";
import { applyFilters, loadRankedDeals } from "@/lib/pipeline";
import { parseSlickdealsXml } from "@/lib/sources/slickdeals";

const NOW = Date.parse("2026-08-15T12:00:00.000Z");

const SAMPLE_RSS = `<?xml version="1.0"?>
<rss version="2.0">
  <channel>
    <item>
      <title><![CDATA[Ainfox 13ft Large Patio Rectangle Umbrella $56.84 + Free S&H]]></title>
      <link>https://slickdeals.net/f/umbrella-test</link>
      <description><![CDATA[Walmart patio umbrella for Arizona-style shade.]]></description>
      <pubDate>Sat, 15 Aug 2026 10:00:00 GMT</pubDate>
    </item>
    <item>
      <title><![CDATA[Ipletix Women's Yoga Lounge Joggers $5.19]]></title>
      <link>https://slickdeals.net/f/joggers-test</link>
      <description><![CDATA[Generic apparel with no local hook.]]></description>
      <pubDate>Sat, 15 Aug 2026 10:00:00 GMT</pubDate>
    </item>
  </channel>
</rss>`;

describe("parseSlickdealsXml", () => {
  it("keeps climate deals and drops unrelated apparel", () => {
    const deals = parseSlickdealsXml(SAMPLE_RSS);
    expect(deals).toHaveLength(1);
    expect(deals[0].askingPrice).toBe(56.84);
    expect(deals[0].category).toBe("outdoor");
    expect(deals[0].title).toMatch(/Patio/);
  });
});

describe("loadRankedDeals", () => {
  it("ranks the catalog without live fetches", async () => {
    const result = await loadRankedDeals({ now: NOW, live: false });
    expect(result.ranked).toBeGreaterThan(20);
    expect(result.deals[0].valueScore).toBeGreaterThan(result.deals.at(-1)!.valueScore);
    expect(result.sources[0]?.id).toBe("catalog");
    expect(result.deals.every((deal) => deal.rank >= 1)).toBe(true);
  });
});

describe("applyFilters", () => {
  it("filters by city, category, and recommendation", async () => {
    const result = await loadRankedDeals({ now: NOW, live: false });
    const tucsonHousing = applyFilters(result.deals, { city: "Tucson", category: "housing" });
    expect(tucsonHousing.length).toBeGreaterThan(0);
    expect(tucsonHousing.every((deal) => deal.city === "Tucson" && deal.category === "housing")).toBe(true);

    const buys = applyFilters(result.deals, { recommendation: "buy", maxPrice: 500 });
    expect(buys.every((deal) => deal.recommendation === "buy" && deal.askingPrice <= 500)).toBe(true);
  });
});
