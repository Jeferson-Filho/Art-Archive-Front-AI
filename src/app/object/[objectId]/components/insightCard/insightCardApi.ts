import axios from "axios";
import { aiAxiosInstance } from "../../../../../libs/axios/axios";
import { BlockName, BlockOutcome } from "./types";

// Response field names of each endpoint (doc 07, §4)
const FIELDS: Record<BlockName, string> = {
  "historical-context": "historical_context",
  "comparative-analysis": "comparative_analysis"
};

/**
 * Fetches one block from the backend — GET /artworks/{artwork_id}/{block}
 * (doc 07, §4) — and reduces the response to a BlockOutcome. Never rejects:
 * every failure becomes an outcome, so the two requests always both settle.
 */
export async function fetchBlock(artworkId: string, block: BlockName): Promise<BlockOutcome> {
  const field = FIELDS[block];
  try {
    const { data } = await aiAxiosInstance.get(`artworks/${artworkId}/${block}`);
    const text = data?.[field];
    const sources = data?.[`${field}_sources`];

    if (typeof text !== "string" || text.trim() === "") return { kind: "empty" };
    return { kind: "content", text, sources: Array.isArray(sources) ? sources.filter(isWebUrl) : [] };
  } catch (error) {
    // 404, 502 and network failures count as a block without content (doc 06, §9)
    return isTimeout(error) ? { kind: "timeout" } : { kind: "empty" };
  }
}

/**
 * Sources are produced by the LLM (RF-009) and rendered as links, so only
 * http(s) URLs are kept — a `javascript:` URL in an href would run on click.
 */
function isWebUrl(source: unknown): source is string {
  if (typeof source !== "string") return false;
  try {
    const { protocol } = new URL(source);
    return protocol === "http:" || protocol === "https:";
  } catch {
    return false;
  }
}

function isTimeout(error: unknown): boolean {
  if (!axios.isAxiosError(error)) return false;
  // The backend's own 60s limit (RNF-002), or the client's (RF-007: "exceed the configured time limit")
  return error.response?.status === 504 || error.code === "ECONNABORTED" || error.code === "ETIMEDOUT";
}
