import { applyFilters, loadRankedDeals } from "@/lib/pipeline";
import type { Recommendation } from "@/lib/types";
import { NextRequest, NextResponse } from "next/server";

export const dynamic = "force-dynamic";

const RECS = new Set(["buy", "watch", "skip", "any"]);

export async function GET(request: NextRequest) {
  const params = request.nextUrl.searchParams;
  const recommendation = params.get("recommendation") ?? "any";
  const result = await loadRankedDeals();
  const deals = applyFilters(result.deals, {
    city: params.get("city") ?? undefined,
    category: params.get("category") ?? undefined,
    maxPrice: numberParam(params.get("maxPrice")),
    minScore: numberParam(params.get("minScore")),
    recommendation: RECS.has(recommendation) ? (recommendation as Recommendation | "any") : "any",
    q: params.get("q") ?? undefined,
  });

  return NextResponse.json({
    ...result,
    deals,
    ranked: deals.length,
  });
}

function numberParam(value: string | null): number | undefined {
  if (!value) return undefined;
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : undefined;
}
