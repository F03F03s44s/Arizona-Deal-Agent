import { describe, expect, it } from "vitest";
import { hashId, normalizeTitle, parseAskingPrice, parsePrices, stripHtml } from "@/lib/parse";

describe("parsePrices", () => {
  it("reads sale prices from Slickdeals-style titles", () => {
    const title = "13' Ainfox Large Patio Umbrella (Khaki or Blue) $56.85 + Free S&H";
    expect(parseAskingPrice(title)).toBe(56.85);
  });

  it("ignores duplicate prices and tiny noise", () => {
    expect(parsePrices("$12 $12 $0.00")).toEqual([12]);
    expect(parseAskingPrice("Save $1 today")).toBeNull();
  });

  it("handles comma-formatted asking prices", () => {
    expect(parseAskingPrice("2016 Honda Civic $9,800 OBO")).toBe(9800);
  });
});

describe("stripHtml", () => {
  it("flattens RSS descriptions", () => {
    expect(stripHtml("<div>Patio <b>set</b>&nbsp;in Tucson</div>")).toBe("Patio set in Tucson");
  });
});

describe("normalizeTitle", () => {
  it("dedupes titles that only differ by price punctuation", () => {
    expect(normalizeTitle("Patio Set — $125!")).toBe(normalizeTitle("patio set $125"));
  });
});

describe("hashId", () => {
  it("is stable for the same input", () => {
    expect(hashId("https://slickdeals.net/f/1")).toBe(hashId("https://slickdeals.net/f/1"));
    expect(hashId("a")).not.toBe(hashId("b"));
  });
});
