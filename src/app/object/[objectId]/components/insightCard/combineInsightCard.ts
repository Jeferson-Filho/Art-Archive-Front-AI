import { BlockName, BlockOutcome, DisplayedBlock, InsightCardState } from "./types";

/**
 * Combines the two independent block responses into the card's single state —
 * the aggregation rule of doc 06 (§5). Called only once both have settled, so
 * the card never shows one block before the other (RF-001).
 *
 * - at least one block has text → displayed, rendering only those blocks (RF-005 scenario 2, RF-007 scenario 1)
 * - neither has text, both timed out → timeout-specific error (RF-007 scenario 3)
 * - neither has text, any other mix → standard error (RF-005 scenario 3, RF-007 scenario 2)
 */
export function combineInsightCard(historical: BlockOutcome, comparative: BlockOutcome): InsightCardState {
  const outcomes: [BlockName, BlockOutcome][] = [
    ["historical-context", historical],
    ["comparative-analysis", comparative]
  ];
  const blocks: DisplayedBlock[] = outcomes.flatMap(([name, outcome]) =>
    outcome.kind === "content" ? [{ name, text: outcome.text, sources: outcome.sources }] : []
  );

  if (blocks.length > 0) return { status: "displayed", blocks };
  if (historical.kind === "timeout" && comparative.kind === "timeout") return { status: "error", reason: "timeout" };
  return { status: "error", reason: "standard" };
}
