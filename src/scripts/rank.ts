import { money, pct } from "../lib/format";
import { loadRankedDeals } from "../lib/pipeline";

async function main() {
  const live = !process.argv.includes("--offline");
  const result = await loadRankedDeals({ live });
  const top = result.deals.slice(0, 15);

  console.log("Arizona Deal Agent — top value");
  console.log(`Scanned ${result.scanned} · ranked ${result.ranked} · ${result.generatedAt}`);
  console.log(
    result.sources
      .map((source) => `${source.label}: ${source.ok ? source.count : source.error ?? "down"}`)
      .join(" · "),
  );
  console.log("");

  for (const deal of top) {
    const save = deal.marketPrice ? `${pct(deal.savingsPct)} vs ${money(deal.marketPrice, true)}` : "no comp";
    console.log(
      `${String(deal.rank).padStart(2, "0")}  ${deal.valueScore.toFixed(1).padStart(5)}  ${deal.recommendation.toUpperCase().padEnd(5)}  ${money(deal.askingPrice, true).padStart(8)}  ${save.padEnd(22)}  ${deal.city.padEnd(11)}  ${deal.title}`,
    );
  }
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
