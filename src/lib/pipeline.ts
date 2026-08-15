import { rankDeals } from "./scoring";
import { loadCatalog } from "./sources/catalog";
import { loadSlickdeals } from "./sources/slickdeals";
import { normalizeTitle } from "./parse";
import type { Deal, DealFilters, PipelineResult, RankedDeal } from "./types";

const CACHE_TTL_MS = 5 * 60 * 1000;

let cache: { at: number; result: PipelineResult } | null = null;

function dedupe(deals: Deal[]): Deal[] {
  const seen = new Set<string>();
  const unique: Deal[] = [];
  for (const deal of deals) {
    const key = `${normalizeTitle(deal.title)}:${Math.round(deal.askingPrice)}`;
    if (seen.has(key)) continue;
    seen.add(key);
    unique.push(deal);
  }
  return unique;
}

export function applyFilters(deals: RankedDeal[], filters: DealFilters = {}): RankedDeal[] {
  const query = filters.q?.trim().toLowerCase();
  return deals.filter((deal) => {
    if (filters.city && filters.city !== "all" && deal.city !== filters.city) return false;
    if (filters.category && filters.category !== "all" && deal.category !== filters.category) return false;
    if (filters.maxPrice && deal.askingPrice > filters.maxPrice) return false;
    if (filters.minScore && deal.valueScore < filters.minScore) return false;
    if (filters.recommendation && filters.recommendation !== "any" && deal.recommendation !== filters.recommendation) {
      return false;
    }
    if (query) {
      const hay = `${deal.title} ${deal.description} ${deal.city} ${deal.tags.join(" ")}`.toLowerCase();
      if (!hay.includes(query)) return false;
    }
    return true;
  });
}

export async function loadRankedDeals(options?: {
  now?: number;
  live?: boolean;
  timeoutMs?: number;
}): Promise<PipelineResult> {
  const now = options?.now ?? Date.now();
  const live = options?.live ?? true;

  if (live && cache && now - cache.at < CACHE_TTL_MS) {
    return cache.result;
  }

  const catalog = loadCatalog(now);
  const liveResult = live
    ? await loadSlickdeals(options?.timeoutMs ?? 8000)
    : { deals: [], sources: [] };

  const merged = dedupe([...liveResult.deals, ...catalog]);
  const ranked = rankDeals(merged, now);

  const result: PipelineResult = {
    deals: ranked,
    scanned: merged.length,
    ranked: ranked.length,
    generatedAt: new Date(now).toISOString(),
    sources: [
      { id: "catalog", label: "Arizona local sample", ok: true, count: catalog.length },
      ...liveResult.sources,
    ],
  };

  if (live) cache = { at: now, result };
  return result;
}

export function clearDealCache(): void {
  cache = null;
}
