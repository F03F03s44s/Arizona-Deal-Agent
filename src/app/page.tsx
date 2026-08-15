import { DealBoard } from "@/components/DealBoard";
import { loadRankedDeals } from "@/lib/pipeline";

export const dynamic = "force-dynamic";

export default async function HomePage() {
  const initial = await loadRankedDeals();
  return <DealBoard initial={initial} />;
}
