"""
On-Demand Persistence module — Insight Card blocks (doc 04 §4; doc 06 §2, §3, §7).

One public function per block, each backing exactly one request handler
(doc 06, §7). The two blocks are checked, generated and persisted
independently: neither function reads or waits on the other's column (RF-001).
"""

import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Literal

import asyncpg
from sqlalchemy import insert, select, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.db.models import ArtworkAIContent, ArtworkContentSource
from app.integrations import harvard
from app.pipeline import generation
from app.pipeline.generation import (
    ArtworkMetadata,
    ImageUnavailableError,
    LLMIncompleteResponseError,
    LLMProviderError,
    TextBlockResult,
)

logger = logging.getLogger(__name__)

BlockType = Literal["historical_context", "comparative_analysis"]

# What "the database is unreadable" means (doc 06, §11 item 2). The driver
# raises connection failures unwrapped — OSError (refused, unreachable,
# TimeoutError) or asyncpg's own errors — not as SQLAlchemy errors, so
# catching SQLAlchemyError alone would let an outage through as a 500.
DATABASE_UNAVAILABLE = (SQLAlchemyError, OSError, asyncpg.PostgresError, asyncpg.InterfaceError)

# Failures that come back as an empty block rather than an error: the same
# outcome as "the model had nothing reliable to say" (doc 09, §10). A timeout
# (LLMTimeoutError) is the exception, and propagates as a 504.
GENERATION_FAILED = (ImageUnavailableError, LLMProviderError, LLMIncompleteResponseError)

GENERATORS: dict[str, Callable[..., Awaitable[TextBlockResult]]] = {
    "historical_context": generation.generate_historical_context,
    "comparative_analysis": generation.generate_comparative_analysis,
}


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
    try:
        persisted = await _read_persisted_block(session, artwork_id, block)
        database_readable = True
    except DATABASE_UNAVAILABLE as exc:
        # Treated as "block missing" (doc 06, §11 item 2): the Insight Card keeps
        # working through an outage. Nothing is persisted while the database is
        # unreadable (doc 06, §7).
        logger.warning("Database unreadable for artwork %s, block treated as missing: %s", artwork_id, type(exc).__name__)
        persisted, database_readable = None, False

    if persisted is not None:
        return persisted

    # The artwork must exist before anything is generated for it (doc 07, §4).
    # Raises harvard.HarvardUnavailableError when Harvard itself fails.
    artwork = await harvard.get_object(artwork_id)
    if artwork is None:
        raise ArtworkNotFoundError(artwork_id)

    try:
        result = await GENERATORS[block](
            artwork.get("primaryimageurl"),
            _metadata_from_record(artwork),
            timeout=get_settings().generation_timeout_seconds,  # RNF-002
        )
    except GENERATION_FAILED as exc:
        # Includes the content-filter blocks, not handled further in this
        # version (doc 99, Decision 10; documentation/Challenges.txt)
        logger.warning("Generation of %s failed for artwork %s: %s: %s", block, artwork_id, type(exc).__name__, exc)
        return TextBlock(text="")

    if result.text == "":
        # RF-002/RF-003 scenario 3, RF-010 scenario 10.2 — not persisted, retried next visit
        return TextBlock(text="")

    if database_readable:
        try:
            await _upsert_if_null(session, artwork_id, block, result)
        except DATABASE_UNAVAILABLE as exc:
            # The visitor still gets the content; the write is retried on a later visit (RF-004 scenario 2)
            await session.rollback()
            logger.error("Could not persist %s for artwork %s: %s", block, artwork_id, type(exc).__name__)
    return TextBlock(text=result.text, sources=result.sources)


def _metadata_from_record(artwork: dict) -> ArtworkMetadata:
    """Maps a Harvard object record onto the pipeline's input (doc 09, §3)."""
    return ArtworkMetadata(
        title=artwork.get("title") or "",
        artists=[
            person["name"]
            for person in artwork.get("people") or []
            if person.get("role") == "Artist" and person.get("name")
        ],
        date_display=artwork.get("dated"),
        period=artwork.get("period"),
        culture=artwork.get("culture"),
        classification=artwork.get("classification"),
        technique=artwork.get("technique"),
        medium=artwork.get("medium"),
    )


async def _upsert_if_null(session: AsyncSession, artwork_id: int, block: BlockType, result: TextBlockResult) -> None:
    """Per-column, first-writer-wins upsert (doc 06, §6).

    `block` is one of the two BlockType literals, never user input, so
    interpolating it as a column name is safe.
    """
    row = await session.execute(
        text(
            f"""
            INSERT INTO artwork_ai_content (
                artwork_id, {block}, {block}_prompt_version, {block}_generated_at, created_at, updated_at
            )
            VALUES (:artwork_id, :text, :prompt_version, now(), now(), now())
            ON CONFLICT (artwork_id) WHERE expired_at IS NULL DO UPDATE SET
                {block}                = EXCLUDED.{block},
                {block}_prompt_version = EXCLUDED.{block}_prompt_version,
                {block}_generated_at   = EXCLUDED.{block}_generated_at,
                updated_at             = now()
            WHERE artwork_ai_content.{block} IS NULL
            RETURNING id
            """
        ),
        {"artwork_id": artwork_id, "text": result.text, "prompt_version": result.prompt_version},
    )
    content_id = row.scalar_one_or_none()

    # Sources follow the winning write only: a request that lost the race
    # never attaches its sources to the winner's text (doc 06, §6)
    if content_id is not None and result.sources:
        await session.execute(
            insert(ArtworkContentSource),
            [{"content_id": content_id, "block_type": block, "url": url} for url in result.sources],
        )
    await session.commit()


async def _read_persisted_block(session: AsyncSession, artwork_id: int, block: BlockType) -> TextBlock | None:
    # At most one active row per artwork (doc 05, §6, Decision 12); retired rows
    # are skipped by the soft-delete filter (doc 05, §8).
    row = (
        await session.execute(
            select(ArtworkAIContent.id, getattr(ArtworkAIContent, block)).where(
                ArtworkAIContent.artwork_id == artwork_id,
                ArtworkAIContent.expired_at.is_(None),
            )
        )
    ).one_or_none()
    if row is None or row[1] is None:
        return None

    content_id, text = row
    sources = await session.scalars(
        select(ArtworkContentSource.url)
        .where(ArtworkContentSource.content_id == content_id, ArtworkContentSource.block_type == block)
        .order_by(ArtworkContentSource.created_at, ArtworkContentSource.id)
    )
    return TextBlock(text=text, sources=list(sources))
