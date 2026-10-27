"""
Insight Card endpoints (doc 07, §4) — one independent endpoint per block.

The front-end fires both in parallel and recombines the two responses into
the Insight Card's single loading/displayed/error state (doc 06, §5). No
endpoint here aggregates them.

`GET /artworks/{artwork_id}/alt-text` is deferred this cycle (doc 99, §2.2).
"""

import logging
from collections.abc import Awaitable

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ErrorResponse, artwork_not_found, harvard_api_error
from app.db.base import get_session
from app.integrations.harvard import HarvardUnavailableError
from app.persistence import insight_card
from app.persistence.insight_card import ArtworkNotFoundError, TextBlock

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/artworks", tags=["Insight Card"])


class HistoricalContextResponse(BaseModel):
    artwork_id: int
    historical_context: str
    historical_context_sources: list[str]


class ComparativeAnalysisResponse(BaseModel):
    artwork_id: int
    comparative_analysis: str
    comparative_analysis_sources: list[str]


ERROR_RESPONSES: dict = {
    400: {"model": ErrorResponse, "description": "`VALIDATION_ERROR` — `artwork_id` is not an integer"},
    404: {"model": ErrorResponse, "description": "`ARTWORK_NOT_FOUND` — the artwork does not exist in the Harvard API"},
    502: {"model": ErrorResponse, "description": "`HARVARD_API_ERROR` — Harvard failed while checking the artwork"},
    504: {"model": ErrorResponse, "description": "`GENERATION_TIMEOUT` — generation exceeded 60s (RNF-002). Reachable once Phase 4 lands."},
}


@router.get(
    "/{artwork_id}/historical-context",
    response_model=HistoricalContextResponse,
    responses=ERROR_RESPONSES,
    summary="Historical context block",
)
async def get_historical_context(
    artwork_id: int, session: AsyncSession = Depends(get_session)
) -> HistoricalContextResponse:
    """Returns the persisted block, or generates it on first visit (doc 06, §2).

    An empty `historical_context` is a normal outcome, not an error: the model
    found nothing reliable to say, or no relevant source (RF-002 scenario 3,
    RF-010 scenario 10.2). It is not persisted, and is retried on the next visit.
    """
    block = await _resolve(insight_card.get_or_generate_historical_context(session, artwork_id), artwork_id)
    return HistoricalContextResponse(
        artwork_id=artwork_id,
        historical_context=block.text,
        historical_context_sources=block.sources,
    )


@router.get(
    "/{artwork_id}/comparative-analysis",
    response_model=ComparativeAnalysisResponse,
    responses=ERROR_RESPONSES,
    summary="Comparative analysis block",
)
async def get_comparative_analysis(
    artwork_id: int, session: AsyncSession = Depends(get_session)
) -> ComparativeAnalysisResponse:
    """Returns the persisted block, or generates it on first visit (doc 06, §3).

    An empty `comparative_analysis` is a normal outcome, not an error
    (RF-003 scenario 3.2, RF-010 scenario 10.2).
    """
    block = await _resolve(insight_card.get_or_generate_comparative_analysis(session, artwork_id), artwork_id)
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
