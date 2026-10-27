"""
On-Demand Persistence module — Insight Card blocks (doc 04 §4; doc 06 §2, §3, §7).

One public function per block, each backing exactly one request handler
(doc 06, §7). The two blocks are checked, generated and persisted
independently: neither function reads or waits on the other's column (RF-001).
"""

from dataclasses import dataclass, field
from typing import Literal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import ArtworkAIContent, ArtworkContentSource
from app.integrations import harvard

BlockType = Literal["historical_context", "comparative_analysis"]


class ArtworkNotFoundError(Exception):
    """The artwork does not exist in the Harvard Art Museums API (doc 07, §4)."""


@dataclass
class TextBlock:
    text: str
    sources: list[str] = field(default_factory=list)


async def get_or_generate_historical_context(session: AsyncSession, artwork_id: int) -> TextBlock:
    """RF-001, RF-002 — doc 06 §2."""
    return await _get_or_generate(session, artwork_id, "historical_context")


async def get_or_generate_comparative_analysis(session: AsyncSession, artwork_id: int) -> TextBlock:
    """RF-001, RF-003 — doc 06 §3."""
    return await _get_or_generate(session, artwork_id, "comparative_analysis")


async def _get_or_generate(session: AsyncSession, artwork_id: int, block: BlockType) -> TextBlock:
    # Check before generating (RF-001). The database is always consulted first,
    # so an already-persisted block never reaches Harvard or the LLM (RNF-001).
    # PROVISIONAL: a failed read is unspecified and currently surfaces as
    # 500 INTERNAL_ERROR through the generic handler — doc 06, §11 item 2.
    persisted = await _read_persisted_block(session, artwork_id, block)
    if persisted is not None:
        return persisted

    # The artwork must exist before anything is generated for it (doc 07, §4).
    # Raises harvard.HarvardUnavailableError when Harvard itself fails.
    artwork = await harvard.get_object(artwork_id)
    if artwork is None:
        raise ArtworkNotFoundError(artwork_id)

    # PROVISIONAL (doc 99, Phase 3): generation is stubbed until Phases 4 and 5
    # wire in the AI pipeline (doc 09). An empty block is also what the endpoint
    # returns when the LLM has nothing reliable to say (RF-002/RF-003, scenario 3),
    # so the contract of doc 07 (§4) already holds.
    return TextBlock(text="")


async def _read_persisted_block(session: AsyncSession, artwork_id: int, block: BlockType) -> TextBlock | None:
    text = await session.scalar(
        select(getattr(ArtworkAIContent, block)).where(
            ArtworkAIContent.artwork_id == artwork_id,
            ArtworkAIContent.expired_at.is_(None),  # soft delete (doc 05, §8)
        )
    )
    if text is None:
        return None

    sources = await session.scalars(
        select(ArtworkContentSource.url)
        .where(ArtworkContentSource.artwork_id == artwork_id, ArtworkContentSource.block_type == block)
        .order_by(ArtworkContentSource.created_at, ArtworkContentSource.id)
    )
    return TextBlock(text=text, sources=list(sources))
