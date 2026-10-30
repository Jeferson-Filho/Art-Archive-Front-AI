import axios from "axios";
import axiosInstance, { aiAxiosInstance } from "../../../../../libs/axios/axios";
import { BlockName, BlockOutcome, LoadBlock } from "./types";

// Response field names of each endpoint (doc 07, §4)
const FIELDS: Record<BlockName, string> = {
  "historical-context": "historical_context",
  "comparative-analysis": "comparative_analysis"
};

// Harvard's image service resizes on request: 768px keeps the image at about
// 100 KB while staying legible to the model (doc 09, §4; doc 06, §5)
const IMAGE_MAX_SIDE_PX = 768;
const IMAGE_DOWNLOAD_TIMEOUT_MS = 10000;

/**
 * The loader for one artwork visit (doc 06 §5; doc 99, Decision 11). Each
 * block is read with GET /artworks/{artwork_id}/{block}; only a block that
 * comes back null is generated, with a POST carrying the artwork's image.
 * The image is downloaded at most once and shared by both blocks.
 */
export function createApiLoader(): LoadBlock {
  let image: Promise<string | null> | undefined;
  return (artworkId, block) => loadBlock(artworkId, block, () => (image ??= downloadArtworkImage(artworkId)));
}

/**
 * Reduces one block's requests to a BlockOutcome. Never rejects: every
 * failure becomes an outcome, so the two blocks always both settle.
 */
async function loadBlock(
  artworkId: string,
  block: BlockName,
  getImage: () => Promise<string | null>
): Promise<BlockOutcome> {
  const field = FIELDS[block];
  try {
    const { data } = await aiAxiosInstance.get(`artworks/${artworkId}/${block}`);
    if (data?.[field] !== null) return toOutcome(data, field);

    // Not persisted yet: generate it from the artwork's image (doc 07, §4)
    const image = await getImage();
    if (image === null) return { kind: "empty" }; // nothing to generate from (doc 06, §9)
    const { data: generated } = await aiAxiosInstance.post(`artworks/${artworkId}/${block}`, { image });
    return toOutcome(generated, field);
  } catch (error) {
    // 400, 404, 502 and network failures count as a block without content (doc 06, §9)
    return isTimeout(error) ? { kind: "timeout" } : { kind: "empty" };
  }
}

function toOutcome(data: Record<string, unknown> | undefined, field: string): BlockOutcome {
  const text = data?.[field];
  const sources = data?.[`${field}_sources`];

  if (typeof text !== "string" || text.trim() === "") return { kind: "empty" };
  return { kind: "content", text, sources: Array.isArray(sources) ? sources.filter(isWebUrl) : [] };
}

/**
 * The artwork's primary image, at most 768px, as a base64 data URL — or null
 * when the artwork has none or it cannot be downloaded (doc 06, §5). The
 * browser fetches it from Harvard's image service, which refuses the deployed
 * backend (doc 04, §9, Decision 8).
 */
async function downloadArtworkImage(artworkId: string): Promise<string | null> {
  try {
    const { data: artwork } = await axiosInstance.get(`proxy/object/${artworkId}`);
    if (typeof artwork?.primaryimageurl !== "string" || artwork.primaryimageurl === "") return null;

    const url = new URL(artwork.primaryimageurl);
    url.searchParams.set("width", String(IMAGE_MAX_SIDE_PX));
    url.searchParams.set("height", String(IMAGE_MAX_SIDE_PX));
    const response = await fetch(url, { signal: AbortSignal.timeout(IMAGE_DOWNLOAD_TIMEOUT_MS) });
    const blob = await response.blob();
    if (!response.ok || !blob.type.startsWith("image/")) return null;
    return await toDataUrl(blob);
  } catch {
    return null;
  }
}

function toDataUrl(blob: Blob): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(reader.result as string);
    reader.onerror = () => reject(reader.error);
    reader.readAsDataURL(blob);
  });
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
