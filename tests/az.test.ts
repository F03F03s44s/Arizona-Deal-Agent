import { describe, expect, it } from "vitest";
import { arizonaFit, climateRelevance, detectCity, isArizonaUseful } from "@/lib/az";

describe("detectCity", () => {
  it("maps Valley place names", () => {
    expect(detectCity("Pickup in Ahwatukee this weekend")).toBe("Phoenix");
    expect(detectCity("Oro Valley duplex")).toBe("Tucson");
    expect(detectCity("Tempe studio near ASU")).toBe("Tempe");
  });

  it("returns null when no Arizona place is present", () => {
    expect(detectCity("Yoga joggers on Amazon")).toBeNull();
  });
});

describe("arizonaFit", () => {
  it("scores local climate deals higher than generic apparel", () => {
    const ac = arizonaFit("Mesa window air conditioner $90");
    const pants = arizonaFit("Women's yoga lounge joggers $5.19");
    expect(ac).toBeGreaterThan(70);
    expect(pants).toBeLessThan(30);
    expect(isArizonaUseful("Women's yoga lounge joggers $5.19")).toBe(false);
    expect(isArizonaUseful("13ft patio umbrella $56")).toBe(true);
  });

  it("treats swamp coolers as climate-relevant", () => {
    expect(climateRelevance("portable swamp cooler for the garage")).toBeGreaterThan(40);
  });
});
