"""0004_create_artwork_ai_content

Creates `artwork_ai_content`, independent of the user-domain tables
(doc 05, §4 and §7, step 4).

Core of the on-demand persistence mechanism. The three content columns are
independently nullable, each with its own prompt version and timestamp,
because each block is checked, generated and persisted on its own
(RF-001 through RF-004, RF-013; doc 05, §6, Decision 8).

The `alt_text*` columns are created here even though Alt Text is deferred
this cycle (doc 99, §2.2) — the schema follows doc 05, and dropping them
would require a second migration to restore later.

Revision ID: 0004
Revises: 0003
"""

import sqlalchemy as sa
from alembic import op

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "artwork_ai_content",
        # Harvard API object ID as the natural key (doc 05, §6, Decision 1)
        sa.Column("artwork_id", sa.Integer(), autoincrement=False, nullable=False),
        sa.Column("historical_context", sa.Text(), nullable=True),
        sa.Column("historical_context_prompt_version", sa.String(length=20), nullable=True),
        sa.Column("historical_context_generated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("comparative_analysis", sa.Text(), nullable=True),
        sa.Column("comparative_analysis_prompt_version", sa.String(length=20), nullable=True),
        sa.Column("comparative_analysis_generated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("alt_text", sa.String(length=300), nullable=True),
        sa.Column("alt_text_prompt_version", sa.String(length=20), nullable=True),
        sa.Column("alt_text_generated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("expired_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "historical_context IS NOT NULL OR comparative_analysis IS NOT NULL OR alt_text IS NOT NULL",
            name="chk_artwork_ai_content_has_block",
        ),
        sa.PrimaryKeyConstraint("artwork_id"),
    )


def downgrade() -> None:
    op.drop_table("artwork_ai_content")
