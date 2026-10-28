"""
AI Pipeline module — the two Insight Card blocks (doc 09).

`generate_historical_context()` and `generate_comparative_analysis()` are
independent entry points (RF-001), each running the same four steps:
download the image (§4), assemble the prompt (§5), call Azure OpenAI (§6),
validate the response structurally (§7). Neither fetches anything from
Harvard: the persistence layer hands over the image URL and metadata (§2).
"""

import base64
import json
import logging
import time
from dataclasses import dataclass, field
from types import ModuleType

import httpx

from app.core.config import get_settings
from app.prompts.comparative_analysis import v1 as comparative_analysis_prompt
from app.prompts.historical_context import v1 as historical_context_prompt

logger = logging.getLogger(__name__)

# Harvard's image service resizes on request; 768px keeps the image at about
# 100 KB and ~500 input tokens while staying legible to the model (doc 09, §4)
IMAGE_MAX_SIDE_PX = 768
IMAGE_DOWNLOAD_TIMEOUT_SECONDS = 10.0
TEMPERATURE = 0.35  # doc 11, §5


class ImageUnavailableError(Exception):
    """Step 1 — the artwork has no image, or it could not be downloaded."""


class LLMTimeoutError(Exception):
    """Step 3 — no answer within the remaining generation budget (RNF-002)."""


class LLMProviderError(Exception):
    """Step 3 — transport error or non-200 answer, including 429 and a content-filtered image."""


class LLMIncompleteResponseError(Exception):
    """Step 4 — the answer is incomplete (e.g. blocked by the content filter) or structurally invalid."""


@dataclass
class ArtworkMetadata:
    """doc 09, §3."""

    title: str
    artists: list[str] = field(default_factory=list)
    date_display: str | None = None
    period: str | None = None
    culture: str | None = None
    classification: str | None = None
    technique: str | None = None
    medium: str | None = None


@dataclass
class TextBlockResult:
    """doc 09, §9."""

    text: str  # "" when the model had nothing reliable to say, or no source survived (RF-010)
    sources: list[str]  # always [] when text == ""
    prompt_version: str  # RNF-006

    def is_structurally_valid(self) -> bool:
        # doc 09, §7: an empty text is a valid outcome, but never with sources
        return (
            isinstance(self.text, str)
            and isinstance(self.sources, list)
            and all(isinstance(url, str) for url in self.sources)
            and (self.sources == [] if self.text == "" else True)
        )


async def generate_historical_context(
    image_url: str | None, metadata: ArtworkMetadata, timeout: float
) -> TextBlockResult:
    """RF-002 — doc 09, with the prompt of doc 11.1."""
    return await _generate(historical_context_prompt, image_url, metadata, timeout)


async def generate_comparative_analysis(
    image_url: str | None, metadata: ArtworkMetadata, timeout: float
) -> TextBlockResult:
    """RF-003 — doc 09, with the prompt of doc 11.2."""
    return await _generate(comparative_analysis_prompt, image_url, metadata, timeout)


async def _generate(
    prompt: ModuleType, image_url: str | None, metadata: ArtworkMetadata, timeout: float
) -> TextBlockResult:
    started = time.monotonic()
    image = await _download_image(image_url)

    # The LLM call gets what is left of the budget once the image is in (doc 09, §6)
    remaining = timeout - (time.monotonic() - started)
    if remaining <= 0:
        raise LLMTimeoutError("budget spent downloading the image")

    response = await _call_llm(prompt, image, metadata, remaining)
    return _parse(response, prompt.PROMPT_VERSION)


async def _download_image(image_url: str | None) -> str:
    """Step 1 (doc 09, §4): Azure cannot fetch Harvard image URLs itself, so
    the image is downloaded here and sent inline as a base64 data URL."""
    if not image_url:
        raise ImageUnavailableError("artwork has no primary image")
    try:
        async with httpx.AsyncClient(timeout=IMAGE_DOWNLOAD_TIMEOUT_SECONDS, follow_redirects=True) as client:
            response = await client.get(image_url, params={"height": IMAGE_MAX_SIDE_PX, "width": IMAGE_MAX_SIDE_PX})
    except httpx.HTTPError as exc:
        raise ImageUnavailableError(type(exc).__name__) from None

    content_type = response.headers.get("content-type", "").split(";")[0].strip()
    if response.status_code != 200 or not content_type.startswith("image/"):
        raise ImageUnavailableError(f"HTTP {response.status_code}, {content_type or 'no content type'}")
    return f"data:{content_type};base64,{base64.b64encode(response.content).decode()}"


async def _call_llm(prompt: ModuleType, image: str, metadata: ArtworkMetadata, timeout: float) -> dict:
    """Step 3 (doc 09, §6): the Responses API, the only one offering web_search.
    No automatic retry (doc 09, §8, decision 3)."""
    settings = get_settings()
    body = {
        "model": settings.azure_openai_deployment,
        "instructions": prompt.SYSTEM_MESSAGE,
        "input": [
            {
                "role": "user",
                "content": [
                    {"type": "input_text", "text": prompt.user_message(metadata)},
                    {"type": "input_image", "image_url": image},
                ],
            }
        ],
        "tools": [{"type": "web_search"}],  # RF-009
        "include": ["web_search_call.action.sources"],
        "text": {
            "format": {"type": "json_schema", "name": prompt.SCHEMA_NAME, "strict": True, "schema": prompt.SCHEMA}
        },
        "temperature": TEMPERATURE,
        "max_output_tokens": prompt.MAX_OUTPUT_TOKENS,
    }
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(
                f"{_api_base_url(settings.azure_openai_endpoint)}/responses",
                headers={"api-key": settings.azure_openai_api_key},
                json=body,
            )
    except httpx.TimeoutException:
        raise LLMTimeoutError(f"no answer within {timeout:.0f}s") from None
    except httpx.HTTPError as exc:
        raise LLMProviderError(type(exc).__name__) from None

    if response.status_code != 200:
        # The provider's error code says why: rate_limit_exceeded, content_policy_violation, ...
        try:
            code = response.json().get("error", {}).get("code")
        except ValueError:
            code = None
        raise LLMProviderError(f"HTTP {response.status_code} {code or ''}".strip())
    try:
        return response.json()
    except ValueError:
        raise LLMProviderError("non-JSON response") from None


def _api_base_url(endpoint: str) -> str:
    # Accepts the resource endpoint with or without the API path the portal
    # shows (".../openai/v1/responses"), so a pasted URL works either way
    return endpoint.split("/openai/")[0].rstrip("/") + "/openai/v1"


def _parse(response: dict, prompt_version: str) -> TextBlockResult:
    """Step 4 (doc 09, §7)."""
    if response.get("status") != "completed":
        # e.g. incomplete_details.reason == "content_filter": the answer was blocked
        raise LLMIncompleteResponseError(f"status {response.get('status')}: {response.get('incomplete_details')}")

    output_text = next(
        (
            content.get("text")
            for item in response.get("output", [])
            if item.get("type") == "message"
            for content in item.get("content", [])
            if content.get("type") == "output_text"
        ),
        None,
    )
    try:
        payload = json.loads(output_text)
    except (TypeError, ValueError):
        raise LLMIncompleteResponseError("no parsable structured output") from None
    if not isinstance(payload, dict):
        raise LLMIncompleteResponseError("structured output is not an object")

    text = payload.get("text")
    result = TextBlockResult(
        text=text.strip() if isinstance(text, str) else text,
        sources=payload.get("sources"),
        prompt_version=prompt_version,
    )
    if not result.is_structurally_valid():
        raise LLMIncompleteResponseError("structurally invalid output")

    usage = response.get("usage", {})
    searches = response.get("tool_usage", {}).get("web_search", {}).get("num_requests")
    logger.info(
        "Generated %s chars and %s sources (%s input / %s output tokens, %s web searches)",
        len(result.text), len(result.sources), usage.get("input_tokens"), usage.get("output_tokens"), searches,
    )
    return result
