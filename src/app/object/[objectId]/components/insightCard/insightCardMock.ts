import { BlockName, BlockOutcome, LoadBlock } from "./types";

/**
 * Mock data source, used while the AI pipeline (doc 99, Phases 4 and 5) is not
 * connected. Selected with NEXT_PUBLIC_INSIGHT_CARD_SOURCE="mock".
 *
 * Each scenario reproduces one Gherkin scenario of doc 02.1, chosen with the
 * `insightCardMock` query parameter, e.g. /object/299843?insightCardMock=both-timeout
 */

export const MOCK_SCENARIOS = [
  "both", //              RF-005 scenarios 1 and 4 (long enough for "See more"), RF-008, RF-010 scenario 1 (default)
  "short", //             RF-005 scenario 4, other side — fits in six lines, so no "See more"
  "historical-only", //   RF-005 scenario 2, RF-007 scenario 1
  "comparative-only", //  RF-005 scenario 2, RF-007 scenario 1
  "both-empty", //        RF-005 scenario 3
  "mixed-failure", //     RF-007 scenario 2 — one timeout, one empty
  "both-timeout", //      RF-007 scenario 3
  "pending" //            RF-006 — never settles, to inspect the loading state
] as const;

export type MockScenario = (typeof MOCK_SCENARIOS)[number];

// Different delays, so the single loading state visibly waits for the slower block (RF-001)
const DELAY_MS: Record<BlockName, number> = {
  "historical-context": 1200,
  "comparative-analysis": 2000
};

// Sized like a real response: 3-5 paragraphs for the historical context (doc 11.1),
// 2-4 for the comparative analysis (doc 11.2) — enough to start collapsed (RF-005 scenario 4)
const CONTENT: Record<BlockName, BlockOutcome> = {
  "historical-context": {
    kind: "content",
    text:
      "Mock historical context — illustrative text shown while the AI pipeline is not yet connected. Once generation " +
      "is live, this block will situate the artwork in its historical period and artistic movement, drawing on the " +
      "artwork's image and its Harvard Art Museums metadata: title, artist, technique, culture and period.\n\n" +
      "A real response opens with the period in which the work was made. It explains what was happening in art at the " +
      "time — which conventions artists were working within, which ones they were starting to question, and where " +
      "this particular work stands between the two. Dates and names appear only when they are well established; " +
      "otherwise the text relies on the broader historical and stylistic context instead of inventing specifics.\n\n" +
      "It then turns to the artistic movement or school the work belongs to, and to the parts of the artist's " +
      "biography that help a reader understand it: where they trained, who they worked alongside, and how this " +
      "work fits into the arc of their career. The aim is a curious adult with no formal training in art history, " +
      "so terms are explained rather than assumed.\n\n" +
      "The block closes on the cultural influences visible in the work — the traditions, exchanges and ideas it " +
      "draws on — synthesized into fluent prose rather than repeating the raw metadata. This fourth paragraph also " +
      "shows how several paragraphs read as continuous text under the single section title, not as a titled " +
      "subsection.",
    sources: ["https://harvardartmuseums.org/collections", "https://www.metmuseum.org/toah/"]
  },
  "comparative-analysis": {
    kind: "content",
    text:
      "Mock comparative analysis — illustrative text. Once generation is live, this block will compare the artwork " +
      "with at least one other artist or work sharing its period, technique or culture, and explain concretely what " +
      "makes them comparable: a shared technique, the same movement, a related cultural context, or a thematic " +
      "parallel.\n\n" +
      "Comparisons are only made when the model is reasonably confident they are accurate. When it is not, this block " +
      "comes back empty and the section shows the historical context alone, with no gap or placeholder where this " +
      "text would have been.\n\n" +
      "It follows the historical context directly, as further paragraphs of the same section, with its own sources " +
      "listed beneath it.",
    sources: ["https://en.wikipedia.org/wiki/Art_history"]
  }
};

const SHORT_CONTENT: Record<BlockName, BlockOutcome> = {
  "historical-context": { kind: "content", text: "Mock historical context — a single short sentence.", sources: [] },
  "comparative-analysis": { kind: "content", text: "Mock comparative analysis — also short.", sources: [] }
};

function outcomeFor(scenario: MockScenario, block: BlockName): BlockOutcome {
  switch (scenario) {
    case "short":
      return SHORT_CONTENT[block];
    case "historical-only":
      return block === "historical-context" ? CONTENT[block] : { kind: "empty" };
    case "comparative-only":
      return block === "comparative-analysis" ? CONTENT[block] : { kind: "empty" };
    case "both-empty":
      return { kind: "empty" };
    case "mixed-failure":
      return block === "historical-context" ? { kind: "timeout" } : { kind: "empty" };
    case "both-timeout":
      return { kind: "timeout" };
    default:
      return CONTENT[block];
  }
}

export function mockScenarioFromUrl(): MockScenario {
  const requested = new URLSearchParams(window.location.search).get("insightCardMock");
  return MOCK_SCENARIOS.find((scenario) => scenario === requested) ?? "both";
}

export function createMockLoader(scenario: MockScenario): LoadBlock {
  return (_artworkId, block) =>
    new Promise((resolve) => {
      if (scenario === "pending") return;
      setTimeout(() => resolve(outcomeFor(scenario, block)), DELAY_MS[block]);
    });
}
