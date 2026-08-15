"use client";

import { categoryLabel, money, pct, timeAgo } from "@/lib/format";
import { CATEGORIES, CITIES, type PipelineResult, type RankedDeal, type Recommendation } from "@/lib/types";
import { useMemo, useState, useTransition } from "react";

type Props = {
  initial: PipelineResult;
};

const REC_OPTIONS: Array<Recommendation | "any"> = ["any", "buy", "watch", "skip"];

export function DealBoard({ initial }: Props) {
  const [data, setData] = useState(initial);
  const [q, setQ] = useState("");
  const [city, setCity] = useState("all");
  const [category, setCategory] = useState("all");
  const [maxPrice, setMaxPrice] = useState("");
  const [recommendation, setRecommendation] = useState<Recommendation | "any">("any");
  const [showMath, setShowMath] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [pending, startTransition] = useTransition();

  const visible = useMemo(() => {
    const query = q.trim().toLowerCase();
    const cap = maxPrice ? Number(maxPrice) : NaN;
    return data.deals.filter((deal) => {
      if (city !== "all" && deal.city !== city) return false;
      if (category !== "all" && deal.category !== category) return false;
      if (Number.isFinite(cap) && deal.askingPrice > cap) return false;
      if (recommendation !== "any" && deal.recommendation !== recommendation) return false;
      if (query) {
        const hay = `${deal.title} ${deal.description} ${deal.city} ${deal.tags.join(" ")}`.toLowerCase();
        if (!hay.includes(query)) return false;
      }
      return true;
    });
  }, [data.deals, q, city, category, maxPrice, recommendation]);

  const buys = data.deals.filter((deal) => deal.recommendation === "buy").length;
  const avgSave = average(
    data.deals.filter((deal) => deal.savings > 0).map((deal) => deal.savingsPct),
  );

  function refresh() {
    startTransition(async () => {
      setError(null);
      try {
        const response = await fetch("/api/deals", { cache: "no-store" });
        if (!response.ok) throw new Error(`Refresh failed (${response.status})`);
        const next = (await response.json()) as PipelineResult;
        setData(next);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Refresh failed");
      }
    });
  }

  return (
    <div className="mx-auto min-h-screen max-w-6xl px-4 pb-20 pt-8 sm:px-6">
      <header className="border-b border-line pb-8">
        <p className="text-xs font-medium tracking-[0.28em] text-copper uppercase">Arizona · value first</p>
        <div className="mt-3 flex flex-wrap items-end justify-between gap-4">
          <div>
            <h1 className="font-display text-4xl leading-none text-ink sm:text-6xl">Arizona Deal Agent</h1>
            <p className="mt-3 max-w-xl text-ink-soft">
              Finds Arizona deals and ranks them by best value — the lowest price that still leaves the most
              profit.
            </p>
          </div>
          <button
            type="button"
            onClick={refresh}
            disabled={pending}
            className="rounded-full bg-ink px-5 py-2.5 text-sm text-sand transition hover:bg-copper disabled:opacity-60"
          >
            {pending ? "Scanning…" : "Rescan live feeds"}
          </button>
        </div>
      </header>

      <section className="mt-6 grid grid-cols-2 gap-3 sm:grid-cols-4">
        <Stat label="Ranked" value={String(data.ranked)} />
        <Stat label="Buy now" value={String(buys)} />
        <Stat label="Avg discount" value={avgSave ? pct(avgSave) : "—"} />
        <Stat
          label="Sources"
          value={`${data.sources.filter((source) => source.ok).length}/${data.sources.length} live`}
        />
      </section>

      <section className="mt-6 rounded-2xl border border-line bg-paper/80 p-4 shadow-[0_1px_0_rgba(27,22,18,0.04)]">
        <div className="grid gap-3 md:grid-cols-5">
          <label className="md:col-span-2">
            <span className="mb-1 block text-xs uppercase tracking-wider text-ink-soft">Search</span>
            <input
              value={q}
              onChange={(event) => setQ(event.target.value)}
              placeholder="AC, duplex, Mesa…"
              className="w-full rounded-xl border border-line bg-sand px-3 py-2 outline-none ring-copper focus:ring-2"
            />
          </label>
          <Select label="City" value={city} onChange={setCity} options={["all", ...CITIES]} />
          <Select label="Category" value={category} onChange={setCategory} options={["all", ...CATEGORIES]} />
          <label>
            <span className="mb-1 block text-xs uppercase tracking-wider text-ink-soft">Max price</span>
            <input
              inputMode="numeric"
              value={maxPrice}
              onChange={(event) => setMaxPrice(event.target.value)}
              placeholder="Any"
              className="w-full rounded-xl border border-line bg-sand px-3 py-2 outline-none ring-copper focus:ring-2"
            />
          </label>
        </div>
        <div className="mt-3 flex flex-wrap items-center gap-2">
          {REC_OPTIONS.map((option) => (
            <button
              key={option}
              type="button"
              onClick={() => setRecommendation(option)}
              className={`rounded-full px-3 py-1 text-sm capitalize ${
                recommendation === option ? "bg-ink text-sand" : "bg-sand-deep text-ink-soft"
              }`}
            >
              {option === "any" ? "All calls" : option}
            </button>
          ))}
          <button
            type="button"
            onClick={() => setShowMath((open) => !open)}
            className="ml-auto text-sm text-copper underline-offset-2 hover:underline"
          >
            {showMath ? "Hide ranking math" : "How value is scored"}
          </button>
        </div>
        {showMath ? <ScoringExplainer /> : null}
        {error ? <p className="mt-3 text-sm text-copper">{error}</p> : null}
      </section>

      <p className="mt-6 text-sm text-ink-soft">
        Showing {visible.length} of {data.ranked} · updated {timeAgo(data.generatedAt)}
      </p>

      <ol className="mt-4 space-y-3">
        {visible.map((deal, index) => (
          <DealCard key={deal.id} deal={deal} displayRank={index + 1} />
        ))}
      </ol>

      {visible.length === 0 ? (
        <p className="mt-10 text-center text-ink-soft">No deals match those filters. Loosen them and scan again.</p>
      ) : null}

      <footer className="mt-12 border-t border-line pt-6 text-sm text-ink-soft">
        <p className="font-medium text-ink">Sources</p>
        <ul className="mt-2 space-y-1">
          {data.sources.map((source) => (
            <li key={source.id}>
              {source.ok ? "●" : "○"} {source.label}
              {source.ok ? ` · ${source.count} kept` : ` · ${source.error ?? "unavailable"}`}
            </li>
          ))}
        </ul>
        <p className="mt-4 max-w-2xl">
          Local Arizona listings are a curated sample so ranking works without scraping classifieds. Live
          national feeds are filtered for Arizona places and desert-climate usefulness, then scored the same
          way.
        </p>
      </footer>
    </div>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-2xl border border-line bg-paper px-4 py-3">
      <p className="text-xs uppercase tracking-wider text-ink-soft">{label}</p>
      <p className="font-display mt-1 text-2xl">{value}</p>
    </div>
  );
}

function Select({
  label,
  value,
  onChange,
  options,
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
  options: readonly string[];
}) {
  return (
    <label>
      <span className="mb-1 block text-xs uppercase tracking-wider text-ink-soft">{label}</span>
      <select
        value={value}
        onChange={(event) => onChange(event.target.value)}
        className="w-full rounded-xl border border-line bg-sand px-3 py-2 capitalize outline-none ring-copper focus:ring-2"
      >
        {options.map((option) => (
          <option key={option} value={option}>
            {option}
          </option>
        ))}
      </select>
    </label>
  );
}

function DealCard({ deal, displayRank }: { deal: RankedDeal; displayRank: number }) {
  const href = deal.url.startsWith("http") ? deal.url : undefined;
  const Wrapper = href ? "a" : "div";
  const scoreColor =
    deal.valueScore >= 80 ? "text-cactus" : deal.valueScore >= 70 ? "text-copper" : "text-gold";

  return (
    <li>
      <Wrapper
        href={href}
        target={href ? "_blank" : undefined}
        rel={href ? "noreferrer" : undefined}
        className="block rounded-2xl border border-line bg-paper p-4 transition hover:border-copper/40 hover:shadow-sm sm:p-5"
      >
        <div className="flex flex-col gap-4 sm:flex-row sm:items-start">
          <div className="flex items-center gap-4 sm:w-36 sm:flex-col sm:items-start">
            <span className="font-display text-3xl text-sand-deep">
              {String(displayRank).padStart(2, "0")}
            </span>
            <div>
              <p className={`font-display text-4xl leading-none ${scoreColor}`}>{deal.valueScore.toFixed(1)}</p>
              <p className="mt-1 text-xs uppercase tracking-wider text-ink-soft">value score</p>
            </div>
          </div>

          <div className="min-w-0 flex-1">
            <div className="flex flex-wrap items-center gap-2">
              <CallBadge call={deal.recommendation} />
              <span className="rounded-full bg-sand px-2 py-0.5 text-xs text-ink-soft">
                {deal.city} · {categoryLabel(deal.category)}
              </span>
              <span className="text-xs text-ink-soft">{timeAgo(deal.postedAt)}</span>
              <span className="text-xs text-ink-soft">{deal.sourceLabel}</span>
            </div>
            <h2 className="font-display mt-2 text-2xl leading-tight">{deal.title}</h2>
            <p className="mt-2 text-sm text-ink-soft">{deal.description}</p>
            <div className="mt-3 flex flex-wrap items-baseline gap-x-4 gap-y-1">
              <p className="text-2xl font-medium">
                {money(deal.askingPrice, true)}
                {deal.pricing === "monthly" ? <span className="text-sm text-ink-soft"> /mo</span> : null}
              </p>
              {deal.marketPrice ? (
                <p className="text-sm text-ink-soft">
                  Typical {money(deal.marketPrice, true)} · {pct(deal.savingsPct)}
                </p>
              ) : null}
              {deal.profit > 0 && deal.category !== "housing" ? (
                <p className="text-sm text-cactus">Est. flip room {money(deal.profit, true)}</p>
              ) : null}
              {deal.capRate ? (
                <p className="text-sm text-cactus">Cap {(deal.capRate * 100).toFixed(1)}%</p>
              ) : null}
            </div>
            <ul className="mt-3 space-y-1 text-sm text-ink-soft">
              {deal.reasons.map((reason) => (
                <li key={reason}>— {reason}</li>
              ))}
            </ul>
          </div>
        </div>
      </Wrapper>
    </li>
  );
}

function CallBadge({ call }: { call: Recommendation }) {
  const styles: Record<Recommendation, string> = {
    buy: "bg-cactus text-white",
    watch: "bg-gold text-ink",
    skip: "bg-sand-deep text-ink-soft",
  };
  return (
    <span className={`rounded-full px-2.5 py-0.5 text-xs font-medium uppercase tracking-wider ${styles[call]}`}>
      {call}
    </span>
  );
}

function ScoringExplainer() {
  return (
    <div className="mt-4 rounded-xl bg-sand px-4 py-3 text-sm text-ink-soft">
      <p>
        Value score is a 0–100 blend: <strong className="text-ink">36% price vs Arizona comps</strong>,{" "}
        <strong className="text-ink">24% profit / cap rate</strong>,{" "}
        <strong className="text-ink">20% affordability</strong>,{" "}
        <strong className="text-ink">10% freshness</strong>,{" "}
        <strong className="text-ink">10% Arizona fit</strong>. Buy means 70+ and a real discount or positive
        flip room. Housing uses estimated cap rate so a cheap duplex can beat a pretty townhome listed at
        comp.
      </p>
    </div>
  );
}

function average(values: number[]): number {
  if (values.length === 0) return 0;
  return values.reduce((sum, value) => sum + value, 0) / values.length;
}
