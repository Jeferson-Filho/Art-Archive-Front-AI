"""
SQLAlchemy models for the five tables of doc 05 (§4).

The DDL in doc 05 is authoritative: column types, nullability, index names
and CHECK constraint names here mirror it exactly. Any divergence is a bug
in this file, not a design choice.

Soft delete (doc 04 §9, Decision 6; doc 05 §6, Decision 11): `users` and
`artwork_ai_content` carry `expired_at`. A NULL means the register is
active; every read of "current" data must filter on `expired_at IS NULL`.
"""

import uuid
from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

# `gen_random_uuid()` comes from the pgcrypto extension (doc 05, §4)
_UUID_PK = text("gen_random_uuid()")


class User(Base):
    """Registered account. Email/password is the sole credential (RF-026)."""

    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, server_default=_UUID_PK)
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    expired_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    sessions: Mapped[list["Session"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    password_reset_tokens: Mapped[list["PasswordResetToken"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )

    __table_args__ = (Index("ux_users_email", "email", unique=True),)


class Session(Base):
    """Backend-issued session, revocable on logout (RF-028)."""

    __tablename__ = "sessions"

    id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, server_default=_UUID_PK)
    user_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    token_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    user: Mapped["User"] = relationship(back_populates="sessions")

    __table_args__ = (
        Index("ux_sessions_token_hash", "token_hash", unique=True),
        Index("ix_sessions_user_id", "user_id"),
        Index("ix_sessions_expires_at", "expires_at"),
    )


class PasswordResetToken(Base):
    """Single-use, expiring reset token (RF-029, RF-030)."""

    __tablename__ = "password_reset_tokens"

    id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, server_default=_UUID_PK)
    user_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    token_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    user: Mapped["User"] = relationship(back_populates="password_reset_tokens")

    __table_args__ = (
        Index("ux_password_reset_tokens_token_hash", "token_hash", unique=True),
        Index("ix_password_reset_tokens_user_id", "user_id"),
    )


class ArtworkAIContent(Base):
    """
    At most one active row per artwork with at least one generated block, plus
    any retired rows (`expired_at` set), which are kept rather than deleted.

    The three content columns are independently nullable and each carries its
    own prompt version and timestamp: they are checked, generated and
    persisted on their own (RF-001, RF-004, RF-013). A row with only
    `historical_context` filled is a normal state, not an anomaly
    (RF-004, scenario 3).

    `alt_text*` is created but left NULL this cycle — Alt Text is deferred
    (doc 99, §2.2); the columns stay so the schema matches doc 05 (§4).
    """

    __tablename__ = "artwork_ai_content"

    # Surrogate key (doc 05, §6, Decision 12): an artwork may keep retired rows
    # beside its single active one, so artwork_id cannot be the primary key.
    id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, server_default=_UUID_PK)
    # Harvard API object ID — unique among active rows only (partial index below)
    artwork_id: Mapped[int] = mapped_column(Integer, nullable=False)

    historical_context: Mapped[str | None] = mapped_column(Text, nullable=True)
    historical_context_prompt_version: Mapped[str | None] = mapped_column(String(20), nullable=True)
    historical_context_generated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    comparative_analysis: Mapped[str | None] = mapped_column(Text, nullable=True)
    comparative_analysis_prompt_version: Mapped[str | None] = mapped_column(String(20), nullable=True)
    comparative_analysis_generated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    alt_text: Mapped[str | None] = mapped_column(String(300), nullable=True)
    alt_text_prompt_version: Mapped[str | None] = mapped_column(String(20), nullable=True)
    alt_text_generated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    expired_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    sources: Mapped[list["ArtworkContentSource"]] = relationship(
        back_populates="artwork", cascade="all, delete-orphan"
    )

    __table_args__ = (
        CheckConstraint(
            "historical_context IS NOT NULL OR comparative_analysis IS NOT NULL OR alt_text IS NOT NULL",
            name="chk_artwork_ai_content_has_block",
        ),
        Index(
            "ux_artwork_ai_content_active_artwork_id",
            "artwork_id",
            unique=True,
            postgresql_where=text("expired_at IS NULL"),
        ),
    )


class ArtworkContentSource(Base):
    """Zero or more sources per generated text block (RF-010)."""

    __tablename__ = "artwork_content_sources"

    id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, server_default=_UUID_PK)
    # The exact row this source was generated for, active or retired (doc 05, §6, Decision 12)
    content_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("artwork_ai_content.id", ondelete="CASCADE"), nullable=False
    )
    block_type: Mapped[str] = mapped_column(String(30), nullable=False)
    url: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    artwork: Mapped["ArtworkAIContent"] = relationship(back_populates="sources")

    __table_args__ = (
        CheckConstraint(
            "block_type IN ('historical_context', 'comparative_analysis')",
            name="chk_sources_block_type",
        ),
        Index("ix_sources_content_block", "content_id", "block_type"),
    )
