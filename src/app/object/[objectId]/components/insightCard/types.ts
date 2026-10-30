/**
 * Insight Card types (doc 06 §5; doc 08 §6).
 *
 * Each of the two blocks is fetched independently and reduced to a
 * BlockOutcome; the two outcomes are then combined into the card's single
 * InsightCardState. The backend never aggregates them — this happens here.
 */

export type BlockName = "historical-context" | "comparative-analysis";

export interface TextBlock {
  text: string;
  sources: string[];
}

/** A block with content, displayed as its own titled section (RF-005). */
export type DisplayedBlock = { name: BlockName } & TextBlock;

/** One block's request, once settled. */
export type BlockOutcome =
  | ({ kind: "content" } & TextBlock)
  // 200 with an empty text (RF-002/RF-003 scenario 3), or any failure that is not a timeout (RF-007 scenario 1)
  | { kind: "empty" }
  // 504 GENERATION_TIMEOUT, or the request exceeded the client's own time limit (RF-007 scenario 3)
  | { kind: "timeout" };

export type InsightCardState =
  | { status: "loading" }
  // Only the non-empty blocks, historical context first (RF-005)
  | { status: "displayed"; blocks: DisplayedBlock[] }
  | { status: "error"; reason: "timeout" | "standard" };

export type LoadBlock = (artworkId: string, block: BlockName) => Promise<BlockOutcome>;
