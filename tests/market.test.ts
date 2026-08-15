import { describe, expect, it } from "vitest";
import { isPlausibleComp, matchMarket } from "@/lib/market";

describe("matchMarket", () => {
  it("does not treat solar lights or air filters as houses", () => {
    const lights = matchMarket("Prime Members: 8-Pk TuyLuxe Solar Pathway Lights $26.50", 26.5);
    expect(lights?.id).toBe("solar-lights");
    expect(lights?.marketPrice).toBe(45);

    const filters = matchMarket("Filtrete 20x30x1 HVAC Furnace Air Filter 6 Pack $61.68", 61.68);
    expect(filters?.id).toBe("hvac-filter");
    expect(filters?.marketPrice).toBe(80);
  });

  it("still matches patio umbrellas and window AC", () => {
    expect(matchMarket("Ainfox 13ft Large Patio Rectangle Umbrella $56.84", 56.84)?.id).toBe("patio-umbrella");
    expect(matchMarket("LG 12,000 BTU window AC, like new", 90)?.id).toBe("window-ac");
  });
});

describe("isPlausibleComp", () => {
  it("rejects a $60 ask against a $385k housing comp", () => {
    expect(isPlausibleComp(61.68, 385000)).toBe(false);
    expect(isPlausibleComp(219000, 268000)).toBe(true);
    expect(isPlausibleComp(8900, 16500)).toBe(true);
  });
});
