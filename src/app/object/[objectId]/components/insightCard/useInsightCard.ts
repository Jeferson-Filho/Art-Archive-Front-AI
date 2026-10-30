"use client";

import { useEffect, useState } from "react";
import { combineInsightCard } from "./combineInsightCard";
import { fetchBlock } from "./insightCardApi";
import { createMockLoader, mockScenarioFromUrl } from "./insightCardMock";
import { InsightCardState, LoadBlock } from "./types";

// "api" unless explicitly set to "mock" — production never silently serves mock data
export const INSIGHT_CARD_SOURCE: "api" | "mock" =
  process.env.NEXT_PUBLIC_INSIGHT_CARD_SOURCE === "mock" ? "mock" : "api";

/**
 * Fires the two block requests in parallel as soon as the artwork page loads,
 * and combines them once both have settled (doc 06 §5; RF-001, RF-006).
 * Neither request waits for the other, nor for the artwork's own details.
 */
export function useInsightCard(artworkId: string): InsightCardState {
  const [state, setState] = useState<InsightCardState>({ status: "loading" });

  useEffect(() => {
    let current = true;
    setState({ status: "loading" });

    const load: LoadBlock = INSIGHT_CARD_SOURCE === "mock" ? createMockLoader(mockScenarioFromUrl()) : fetchBlock;

    // Both loaders resolve to an outcome and never reject, so this waits for
    // both to settle — the Promise.allSettled behaviour doc 06 (§5) requires.
    Promise.all([load(artworkId, "historical-context"), load(artworkId, "comparative-analysis")]).then(
      ([historical, comparative]) => {
        if (current) setState(combineInsightCard(historical, comparative));
      }
    );

    return () => {
      current = false;
    };
  }, [artworkId]);

  return state;
}
