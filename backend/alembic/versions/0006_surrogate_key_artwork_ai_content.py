"""0006_surrogate_key_artwork_ai_content

Applies doc 05 v2.2, Decision 12 (doc 05, §7, step 6).

`artwork_ai_content` moves from `artwork_id` as its primary key to a
surrogate `id`, with a partial unique index on `artwork_id WHERE expired_at
IS NULL`. With `artwork_id` as the key, a soft-deleted row was the only row
an artwork could ever have, so the per-column upsert of doc 06 (§6) kept
conflicting with it and the artwork could never be persisted again. Now a
retired row is preserved and a fresh active row is created beside it.

`artwork_content_sources` follows: it references its parent through
`content_id`, since `artwork_id` is no longer unique. Existing sources are
backfilled from their current parent row.

Revision ID: 0006
Revises: 0005
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # gen_random_uuid() is volatile, so every existing row gets its own id
    op.add_column(
        "artwork_ai_content",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
    )

    op.add_column("artwork_content_sources", sa.Column("content_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.execute(
        "UPDATE artwork_content_sources s SET content_id = c.id "
        "FROM artwork_ai_content c WHERE c.artwork_id = s.artwork_id"
    )
    op.alter_column("artwork_content_sources", "content_id", nullable=False)

    op.drop_constraint("artwork_content_sources_artwork_id_fkey", "artwork_content_sources", type_="foreignkey")
    op.drop_index("ix_sources_artwork_block", table_name="artwork_content_sources")
    op.drop_column("artwork_content_sources", "artwork_id")

    op.drop_constraint("artwork_ai_content_pkey", "artwork_ai_content", type_="primary")
    op.create_primary_key("artwork_ai_content_pkey", "artwork_ai_content", ["id"])
    op.create_index(
        "ux_artwork_ai_content_active_artwork_id",
        "artwork_ai_content",
        ["artwork_id"],
        unique=True,
        postgresql_where=sa.text("expired_at IS NULL"),
    )

    op.create_foreign_key(
        "artwork_content_sources_content_id_fkey",
        "artwork_content_sources",
        "artwork_ai_content",
        ["content_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_index("ix_sources_content_block", "artwork_content_sources", ["content_id", "block_type"])


def downgrade() -> None:
    # artwork_id can only become the primary key again while it is unique
    # across all rows, retired ones included.
    conn = op.get_bind()
    duplicated = conn.execute(
        sa.text("SELECT COUNT(*) FROM (SELECT 1 FROM artwork_ai_content GROUP BY artwork_id HAVING COUNT(*) > 1) d")
    ).scalar()
    if duplicated:
        raise RuntimeError(
            f"Cannot downgrade 0006: {duplicated} artwork(s) have more than one row (a retired row beside an "
            "active one). artwork_id would no longer be unique, so it cannot be restored as the primary key."
        )

    op.drop_index("ix_sources_content_block", table_name="artwork_content_sources")
    op.drop_constraint("artwork_content_sources_content_id_fkey", "artwork_content_sources", type_="foreignkey")

    op.add_column("artwork_content_sources", sa.Column("artwork_id", sa.Integer(), nullable=True))
    op.execute(
        "UPDATE artwork_content_sources s SET artwork_id = c.artwork_id "
        "FROM artwork_ai_content c WHERE c.id = s.content_id"
    )
    op.alter_column("artwork_content_sources", "artwork_id", nullable=False)
    op.drop_column("artwork_content_sources", "content_id")

    op.drop_index("ux_artwork_ai_content_active_artwork_id", table_name="artwork_ai_content")
    op.drop_constraint("artwork_ai_content_pkey", "artwork_ai_content", type_="primary")
    op.create_primary_key("artwork_ai_content_pkey", "artwork_ai_content", ["artwork_id"])
    op.drop_column("artwork_ai_content", "id")

    op.create_foreign_key(
        "artwork_content_sources_artwork_id_fkey",
        "artwork_content_sources",
        "artwork_ai_content",
        ["artwork_id"],
        ["artwork_id"],
        ondelete="CASCADE",
    )
    op.create_index("ix_sources_artwork_block", "artwork_content_sources", ["artwork_id", "block_type"])
