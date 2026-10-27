"""0005_create_artwork_content_sources

Creates `artwork_content_sources`, dependent on `artwork_ai_content`
(doc 05, §4 and §7, step 5).

A relational child table rather than a JSON column, so each source URL stays
queryable and a variable number of sources per block is natural (RF-010;
doc 05, §6, Decision 9). Alt Text has no sources — hence the CHECK on
`block_type`.

Revision ID: 0005
Revises: 0004
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "artwork_content_sources",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("artwork_id", sa.Integer(), nullable=False),
        sa.Column("block_type", sa.String(length=30), nullable=False),
        sa.Column("url", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint(
            "block_type IN ('historical_context', 'comparative_analysis')",
            name="chk_sources_block_type",
        ),
        sa.ForeignKeyConstraint(["artwork_id"], ["artwork_ai_content.artwork_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_sources_artwork_block", "artwork_content_sources", ["artwork_id", "block_type"])


def downgrade() -> None:
    op.drop_index("ix_sources_artwork_block", table_name="artwork_content_sources")
    op.drop_table("artwork_content_sources")
