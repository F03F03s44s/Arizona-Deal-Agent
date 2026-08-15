import { arizonaFit, detectCity, isArizonaUseful } from "../az";
import { inferCategory, matchMarket } from "../market";
import { hashId, parseAskingPrice, parseRssDate, stripHtml } from "../parse";
import type { Deal, SourceStatus } from "../types";
import { XMLParser } from "fast-xml-parser";

const FEEDS = [
  {
    id: "slickdeals-climate",
    label: "Slickdeals climate & shade",
    url: "https://slickdeals.net/newsearch.php?q=air+conditioner+OR+patio+OR+solar+OR+canopy+OR+cooler&searcharea=deals&searchin=first&rss=1",
  },
  {
    id: "slickdeals-az",
    label: "Slickdeals Arizona mentions",
    url: "https://slickdeals.net/newsearch.php?q=phoenix+OR+tucson+OR+arizona&searcharea=deals&searchin=first&rss=1",
  },
  {
    id: "slickdeals-front",
    label: "Slickdeals frontpage",
    url: "https://slickdeals.net/newsearch.php?mode=frontpage&searcharea=deals&searchin=first&rss=1",
  },
] as const;

const parser = new XMLParser({
  ignoreAttributes: false,
  trimValues: true,
  cdataPropName: "#text",
});

type RssText = string | { "#text"?: string } | Array<string | { "#text"?: string }>;

type RssItem = {
  title?: RssText;
  link?: RssText;
  description?: RssText;
  pubDate?: string;
  "content:encoded"?: RssText;
};

function textOf(value: RssText | undefined): string {
  if (!value) return "";
  if (typeof value === "string") return value;
  if (Array.isArray(value)) return value.map((part) => textOf(part)).filter(Boolean).join(" ");
  return value["#text"] ?? "";
}

function itemsFromXml(xml: string): RssItem[] {
  const parsed = parser.parse(xml) as {
    rss?: { channel?: { item?: RssItem | RssItem[] } };
  };
  const item = parsed.rss?.channel?.item;
  if (!item) return [];
  return Array.isArray(item) ? item : [item];
}

function toDeal(item: RssItem, sourceId: string): Deal | null {
  const title = stripHtml(textOf(item.title));
  const description = stripHtml(textOf(item.description) || textOf(item["content:encoded"]));
  const blob = `${title} ${description}`;
  if (!title || !isArizonaUseful(blob, 26)) return null;

  const askingPrice = parseAskingPrice(blob);
  if (!askingPrice) return null;

  const comp = matchMarket(blob, askingPrice);
  const city = detectCity(blob) ?? "Statewide";
  const marketPrice = comp?.marketPrice ?? null;
  const estimatedResale = marketPrice ? Math.round(marketPrice * (comp?.resaleHaircut ?? 0.75)) : null;
  const url = textOf(item.link) || "https://slickdeals.net/";

  return {
    id: `slickdeals:${hashId(url || title)}`,
    title,
    description: description.slice(0, 280),
    category: comp?.category ?? inferCategory(blob, askingPrice),
    city,
    askingPrice,
    marketPrice,
    estimatedResale,
    monthlyRent: null,
    condition: "new",
    pricing: "sale",
    kind: "national",
    source: sourceId,
    sourceLabel: "Slickdeals",
    url,
    postedAt: parseRssDate(item.pubDate),
    tags: ["live", "slickdeals"],
    arizonaFit: arizonaFit(blob),
  };
}

async function fetchFeed(
  feed: (typeof FEEDS)[number],
  timeoutMs: number,
): Promise<{ deals: Deal[]; status: SourceStatus }> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  try {
    const response = await fetch(feed.url, {
      signal: controller.signal,
      headers: {
        "User-Agent": "ArizonaDealAgent/0.1 (+https://github.com/F03F03s44s/Arizona-Deal-Agent)",
        Accept: "application/rss+xml, application/xml, text/xml",
      },
      cache: "no-store",
    });
    if (!response.ok) {
      return {
        deals: [],
        status: { id: feed.id, label: feed.label, ok: false, count: 0, error: `HTTP ${response.status}` },
      };
    }
    const xml = await response.text();
    const deals = itemsFromXml(xml)
      .map((item) => toDeal(item, feed.id))
      .filter((deal): deal is Deal => deal !== null);
    return { deals, status: { id: feed.id, label: feed.label, ok: true, count: deals.length } };
  } catch (error) {
    const message = error instanceof Error ? error.message : "fetch failed";
    return { deals: [], status: { id: feed.id, label: feed.label, ok: false, count: 0, error: message } };
  } finally {
    clearTimeout(timer);
  }
}

export async function loadSlickdeals(timeoutMs = 8000): Promise<{
  deals: Deal[];
  sources: SourceStatus[];
}> {
  const results = await Promise.all(FEEDS.map((feed) => fetchFeed(feed, timeoutMs)));
  const deals = results.flatMap((result) => result.deals);
  const sources = results.map((result) => result.status);
  return { deals, sources };
}

export function parseSlickdealsXml(xml: string, sourceId = "slickdeals-test"): Deal[] {
  return itemsFromXml(xml)
    .map((item) => toDeal(item, sourceId))
    .filter((deal): deal is Deal => deal !== null);
}
