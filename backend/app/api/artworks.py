"""
Insight Card endpoints (doc 07 v2.4, §4) — independent endpoints per block.

Each block has a GET that only reads it, answering null when it is missing,
and a POST that generates it from the artwork's image, which the front-end
downloads and sends: the deployed backend cannot download it from Harvard's
image server (doc 99, Decision 11). The front-end fires the blocks' requests
in parallel and recombines them into the Insight Card's single
loading/displayed/error state (doc 06, §5). No endpoint here aggregates them.

`GET /artworks/{artwork_id}/alt-text` is deferred this cycle (doc 99, §2.2).
"""

import base64
import binascii
import logging
import re
from collections.abc import Awaitable

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ErrorResponse, artwork_not_found, generation_timeout, harvard_api_error
from app.db.base import get_session
from app.integrations.harvard import HarvardUnavailableError
from app.persistence import insight_card
from app.persistence.insight_card import ArtworkNotFoundError, TextBlock
from app.pipeline.generation import LLMTimeoutError

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/artworks", tags=["Insight Card"])

# The image accepted by the POSTs (doc 07, §4): JPEG, PNG or WebP, at most
# 1.5 MB decoded, recognised by its own signature bytes and not only by the
# type it declares
MAX_IMAGE_BYTES = 1_572_864
IMAGE_SIGNATURES = {
    "image/jpeg": lambda data: data.startswith(b"\xff\xd8\xff"),
    "image/png": lambda data: data.startswith(b"\x89PNG\r\n\x1a\n"),
    "image/webp": lambda data: data[:4] == b"RIFF" and data[8:12] == b"WEBP",
}
DATA_URL = re.compile(r"data:(image/[a-z]+);base64,(.+)", re.DOTALL)
# Base64 of MAX_IMAGE_BYTES plus the "data:image/...;base64," prefix, so an
# oversized body is refused before it is decoded
MAX_IMAGE_DATA_URL_CHARS = 4 * -(-MAX_IMAGE_BYTES // 3) + 32


class HistoricalContextResponse(BaseModel):
    artwork_id: int
    historical_context: str | None  # null on the GET when the block is missing
    historical_context_sources: list[str]


class ComparativeAnalysisResponse(BaseModel):
    artwork_id: int
    comparative_analysis: str | None  # null on the GET when the block is missing
    comparative_analysis_sources: list[str]


class GenerateRequest(BaseModel):
    """Body of the Insight Card POSTs (doc 07, §4). Invalid → 400 VALIDATION_ERROR."""

    image: str = Field(
        max_length=MAX_IMAGE_DATA_URL_CHARS,
        description="The artwork's primary image, at most 768px, as a base64 `data:` URL (JPEG, PNG or WebP, up to 1.5 MB)",
    )

    @field_validator("image")
    @classmethod
    def _valid_image(cls, value: str) -> str:
        match = DATA_URL.fullmatch(value)
        if match is None:
            raise ValueError("must be a base64 data: URL")
        media_type, payload = match.groups()
        if media_type not in IMAGE_SIGNATURES:
            raise ValueError("must be a JPEG, PNG or WebP image")
        try:
            data = base64.b64decode(payload, validate=True)
        except binascii.Error:
            raise ValueError("is not valid base64") from None
        if len(data) > MAX_IMAGE_BYTES:
            raise ValueError("exceeds 1.5 MB")
        if not IMAGE_SIGNATURES[media_type](data):
            raise ValueError("does not match its declared type")
        return value


READ_ERROR_RESPONSES: dict = {
    400: {"model": ErrorResponse, "description": "`VALIDATION_ERROR` — `artwork_id` is not an integer"},
}

GENERATE_ERROR_RESPONSES: dict = {
    400: {"model": ErrorResponse, "description": "`VALIDATION_ERROR` — `artwork_id` is not an integer, or the image is invalid"},
    404: {"model": ErrorResponse, "description": "`ARTWORK_NOT_FOUND` — the artwork does not exist in the Harvard API"},
    502: {"model": ErrorResponse, "description": "`HARVARD_API_ERROR` — Harvard failed while checking the artwork"},
    504: {"model": ErrorResponse, "description": "`GENERATION_TIMEOUT` — generation exceeded 60s (RNF-002)"},
}


@router.get(
    "/{artwork_id}/historical-context",
    response_model=HistoricalContextResponse,
    responses=READ_ERROR_RESPONSES,
    summary="Read the historical context block",
)
async def get_historical_context(
    artwork_id: int, session: AsyncSession = Depends(get_session)
) -> HistoricalContextResponse:
    """Returns the persisted block, or `historical_context: null` when it is
    missing — the front-end then sends the POST (doc 06, §2). Never contacts
    Harvard or the LLM (RNF-001)."""
    block = await insight_card.read_historical_context(session, artwork_id)
    return HistoricalContextResponse(
        artwork_id=artwork_id,
        historical_context=block.text if block else None,
        historical_context_sources=block.sources if block else [],
    )


@router.post(
    "/{artwork_id}/historical-context",
    response_model=HistoricalContextResponse,
    responses=GENERATE_ERROR_RESPONSES,
    summary="Generate the historical context block from the artwork's image",
)
async def post_historical_context(
    artwork_id: int, request: GenerateRequest, session: AsyncSession = Depends(get_session)
) -> HistoricalContextResponse:
    """Generates the block from the received image, unless it was persisted in
    the meantime (doc 06, §2).

    An empty `historical_context` is a normal outcome, not an error: the model
    found nothing reliable to say, or no relevant source (RF-002 scenario 3,
    RF-010 scenario 10.2). It is not persisted, and is retried on the next visit.
    """
    block = await _resolve(insight_card.generate_historical_context(session, artwork_id, request.image), artwork_id)
    return HistoricalContextResponse(
        artwork_id=artwork_id,
        historical_context=block.text,
        historical_context_sources=block.sources,
    )


@router.get(
    "/{artwork_id}/comparative-analysis",
    response_model=ComparativeAnalysisResponse,
    responses=READ_ERROR_RESPONSES,
    summary="Read the comparative analysis block",
)
async def get_comparative_analysis(
    artwork_id: int, session: AsyncSession = Depends(get_session)
) -> ComparativeAnalysisResponse:
    """Returns the persisted block, or `comparative_analysis: null` when it is
    missing (doc 06, §3). Never contacts Harvard or the LLM (RNF-001)."""
    block = await insight_card.read_comparative_analysis(session, artwork_id)
    return ComparativeAnalysisResponse(
        artwork_id=artwork_id,
        comparative_analysis=block.text if block else None,
        comparative_analysis_sources=block.sources if block else [],
    )


@router.post(
    "/{artwork_id}/comparative-analysis",
    response_model=ComparativeAnalysisResponse,
    responses=GENERATE_ERROR_RESPONSES,
    summary="Generate the comparative analysis block from the artwork's image",
)
async def post_comparative_analysis(
    artwork_id: int, request: GenerateRequest, session: AsyncSession = Depends(get_session)
) -> ComparativeAnalysisResponse:
    """Generates the block from the received image, unless it was persisted in
    the meantime (doc 06, §3).

    An empty `comparative_analysis` is a normal outcome, not an error
    (RF-003 scenario 3.2, RF-010 scenario 10.2).
    """
    block = await _resolve(insight_card.generate_comparative_analysis(session, artwork_id, request.image), artwork_id)
    return ComparativeAnalysisResponse(
        artwork_id=artwork_id,
        comparative_analysis=block.text,
        comparative_analysis_sources=block.sources,
    )


async def _resolve(pending: Awaitable[TextBlock], artwork_id: int) -> TextBlock:
    """Maps the persistence module's failures onto the error catalog (doc 07, §6)."""
    try:
        return await pending
    except ArtworkNotFoundError:
        raise artwork_not_found(artwork_id) from None
    except HarvardUnavailableError as exc:
        logger.warning("Harvard unavailable while checking artwork %s: %s", artwork_id, exc)
        raise harvard_api_error() from None
    except LLMTimeoutError as exc:
        # The only generation failure that is not an empty block (doc 09, §10)
        logger.warning("Generation timed out for artwork %s: %s", artwork_id, exc)
        raise generation_timeout() from None
