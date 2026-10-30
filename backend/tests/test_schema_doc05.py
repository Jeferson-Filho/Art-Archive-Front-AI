"""
Schema conformance tests for doc 05 (§4) — doc 99, Phase 2 acceptance.

Runs against the migrated database named by DATABASE_URL. Unlike the Phase 1
proxy tests, these need a real PostgreSQL: they assert on catalog contents,
which no stub can stand in for.

    alembic upgrade head && PYTHONPATH=. python tests/test_schema_doc05.py

Behavioural checks run inside a transaction that is rolled back, so the
database is left exactly as found.
"""

import asyncio
import sys

from sqlalchemy import text

from app.db.base import get_engine

failures: list[str] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + (f"  {detail}" if detail and not ok else ""))
    if not ok:
        failures.append(name)


# Exactly what doc 05 (§4) specifies
EXPECTED_TABLES = {
    "users",
    "sessions",
    "password_reset_tokens",
    "artwork_ai_content",
    "artwork_content_sources",
}
EXPECTED_INDEXES = {
    "ux_users_email",
    "ux_sessions_token_hash",
    "ix_sessions_user_id",
    "ix_sessions_expires_at",
    "ux_password_reset_tokens_token_hash",
    "ix_password_reset_tokens_user_id",
    "ux_artwork_ai_content_active_artwork_id",
    "ix_sources_content_block",
}
EXPECTED_CHECKS = {"chk_artwork_ai_content_has_block", "chk_sources_block_type"}

NULLABLE_COLUMNS = (
    "historical_context",
    "comparative_analysis",
    "alt_text",
    "historical_context_prompt_version",
    "comparative_analysis_prompt_version",
    "alt_text_prompt_version",
    "expired_at",
)

# The upsert of doc 06 (§6), targeting the partial unique index of doc 05 (§6, Decision 12)
UPSERT_SQL = (
    "INSERT INTO artwork_ai_content (artwork_id, {col}, created_at, updated_at) "
    "VALUES (:artwork_id, :val, now(), now()) "
    "ON CONFLICT (artwork_id) WHERE expired_at IS NULL DO UPDATE SET {col} = EXCLUDED.{col}, "
    "updated_at = now() WHERE artwork_ai_content.{col} IS NULL "
    "RETURNING id"
)


async def check_catalog(conn) -> None:
    print("\nTables (doc 05 §4)")
    rows = await conn.execute(
        text("SELECT tablename FROM pg_tables WHERE schemaname='public' AND tablename <> 'alembic_version'")
    )
    tables = {r[0] for r in rows}
    check("all five tables present", tables == EXPECTED_TABLES, f"got {sorted(tables)}")

    print("\nIndexes — exact names required by doc 05 §4")
    rows = await conn.execute(
        text(
            "SELECT indexname FROM pg_indexes WHERE schemaname='public' "
            "AND indexname NOT LIKE '%_pkey' AND indexname NOT LIKE 'alembic%'"
        )
    )
    present = {r[0] for r in rows}
    for name in sorted(EXPECTED_INDEXES):
        check(name, name in present)

    print("\nCHECK constraints — exact names required by doc 05 §4")
    rows = await conn.execute(
        text("SELECT conname FROM pg_constraint WHERE contype='c' AND connamespace='public'::regnamespace")
    )
    present = {r[0] for r in rows}
    for name in sorted(EXPECTED_CHECKS):
        check(name, name in present)

    print("\nartwork_ai_content: three independently nullable blocks (RF-001, RF-004)")
    rows = await conn.execute(
        text(
            "SELECT column_name, is_nullable FROM information_schema.columns "
            "WHERE table_schema='public' AND table_name='artwork_ai_content'"
        )
    )
    nullable = {row[0]: row[1] for row in rows.all()}
    for col in NULLABLE_COLUMNS:
        check(f"{col} nullable", nullable.get(col) == "YES", f"got {nullable.get(col)}")
    check("created_at NOT NULL", nullable.get("created_at") == "NO")
    check("id NOT NULL", nullable.get("id") == "NO")
    check("artwork_id NOT NULL", nullable.get("artwork_id") == "NO")

    print("\nartwork_ai_content keys (doc 05 §6, Decision 12)")
    result = await conn.execute(
        text(
            "SELECT a.attname FROM pg_index i JOIN pg_attribute a "
            "ON a.attrelid = i.indrelid AND a.attnum = ANY(i.indkey) "
            "WHERE i.indrelid = 'artwork_ai_content'::regclass AND i.indisprimary"
        )
    )
    check("primary key is the surrogate id", [r[0] for r in result] == ["id"])
    result = await conn.execute(
        text("SELECT indexdef FROM pg_indexes WHERE indexname = 'ux_artwork_ai_content_active_artwork_id'")
    )
    indexdef = result.scalar() or ""
    check(
        "artwork_id unique among active rows only",
        "UNIQUE" in indexdef and "(artwork_id)" in indexdef and "WHERE (expired_at IS NULL)" in indexdef,
        indexdef,
    )
    result = await conn.execute(
        text(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_schema='public' AND table_name='artwork_content_sources'"
        )
    )
    source_columns = {r[0] for r in result}
    check("sources reference content_id, not artwork_id", "content_id" in source_columns and "artwork_id" not in source_columns)

    print("\nSoft delete column present on both tables (doc 05 §6, Decision 11)")
    for table in ("users", "artwork_ai_content"):
        result = await conn.execute(
            text(
                "SELECT 1 FROM information_schema.columns WHERE table_schema='public' "
                "AND table_name=:t AND column_name='expired_at'"
            ),
            {"t": table},
        )
        check(f"{table}.expired_at", result.scalar() == 1)


async def expect_rejected(conn, name: str, statement: str, constraint: str) -> None:
    """Run a statement that must violate `constraint`, leaving the transaction usable."""
    await conn.execute(text("SAVEPOINT sp"))
    try:
        await conn.execute(text(statement))
    except Exception as exc:
        check(name, constraint in str(exc), f"wrong error: {exc}")
    else:
        check(name, False, "the row was accepted")
    await conn.execute(text("ROLLBACK TO SAVEPOINT sp"))


async def check_behaviour(conn) -> None:
    print("\nPartial row — only historical_context (RF-004, scenario 3)")
    await conn.execute(
        text(
            "INSERT INTO artwork_ai_content (artwork_id, historical_context, "
            "historical_context_prompt_version, historical_context_generated_at) "
            "VALUES (-1, 'ctx', 'v1', now())"
        )
    )
    result = await conn.execute(
        text("SELECT comparative_analysis IS NULL AND alt_text IS NULL FROM artwork_ai_content WHERE artwork_id=-1")
    )
    check("inserts with the other two blocks NULL", result.scalar() is True)

    print("\nPer-column, first-writer-wins upsert (doc 06 §6)")
    upsert_comparative = text(UPSERT_SQL.format(col="comparative_analysis"))
    returned = (await conn.execute(upsert_comparative, {"artwork_id": -1, "val": "first"})).scalar()
    result = await conn.execute(
        text("SELECT id, historical_context, comparative_analysis FROM artwork_ai_content WHERE artwork_id=-1")
    )
    row_id, historical, comparative = result.one()
    check("merges into the same row, preserving the other block", historical == "ctx" and comparative == "first")
    check("the winning write returns the row's id", returned == row_id)

    returned = (await conn.execute(upsert_comparative, {"artwork_id": -1, "val": "second"})).scalar()
    result = await conn.execute(text("SELECT comparative_analysis FROM artwork_ai_content WHERE artwork_id=-1"))
    check("second write to the same block is discarded", result.scalar() == "first")
    check("a discarded write returns no id, so it attaches no sources", returned is None)

    print("\nCHECK constraints reject invalid rows")
    await expect_rejected(
        conn,
        "row with all three blocks NULL rejected",
        "INSERT INTO artwork_ai_content (artwork_id) VALUES (-2)",
        "chk_artwork_ai_content_has_block",
    )
    await expect_rejected(
        conn,
        "block_type 'alt_text' rejected (RF-010)",
        f"INSERT INTO artwork_content_sources (content_id, block_type, url) VALUES ('{row_id}', 'alt_text', 'u')",
        "chk_sources_block_type",
    )

    print("\nRetiring an artwork's content (doc 05 §6, Decision 12)")
    await conn.execute(
        text(
            "INSERT INTO artwork_content_sources (content_id, block_type, url) "
            "VALUES (:id, 'historical_context', 'https://example.org/old')"
        ),
        {"id": row_id},
    )
    await expect_rejected(
        conn,
        "a second active row for the same artwork is rejected",
        "INSERT INTO artwork_ai_content (artwork_id, historical_context) VALUES (-1, 'duplicate')",
        "ux_artwork_ai_content_active_artwork_id",
    )
    await conn.execute(text("UPDATE artwork_ai_content SET expired_at = now() WHERE id = :id"), {"id": row_id})
    upsert_historical = text(UPSERT_SQL.format(col="historical_context"))
    new_id = (await conn.execute(upsert_historical, {"artwork_id": -1, "val": "regenerated"})).scalar()
    check("after retirement, the upsert creates a fresh active row", new_id is not None and new_id != row_id)
    result = await conn.execute(
        text("SELECT historical_context, expired_at IS NOT NULL FROM artwork_ai_content WHERE id = :id"),
        {"id": row_id},
    )
    old_text, old_retired = result.one()
    check("the retired row is preserved untouched", old_text == "ctx" and old_retired is True)
    result = await conn.execute(
        text("SELECT COUNT(*) FROM artwork_content_sources WHERE content_id = :id"), {"id": row_id}
    )
    check("the retired row keeps its own sources", result.scalar() == 1)
    result = await conn.execute(
        text("SELECT COUNT(*) FROM artwork_content_sources WHERE content_id = :id"), {"id": new_id}
    )
    check("the fresh row starts with no sources", result.scalar() == 0)

    print("\nON DELETE CASCADE from artwork_ai_content to its sources")
    await conn.execute(text("DELETE FROM artwork_ai_content WHERE id = :id"), {"id": row_id})
    result = await conn.execute(
        text("SELECT COUNT(*) FROM artwork_content_sources WHERE content_id = :id"), {"id": row_id}
    )
    check("sources removed with their parent row", result.scalar() == 0)


async def main() -> None:
    engine = get_engine()

    async with engine.connect() as conn:
        await check_catalog(conn)

    async with engine.connect() as conn:
        transaction = await conn.begin()
        await check_behaviour(conn)
        await transaction.rollback()

    await engine.dispose()

    print()
    if failures:
        print(f"{len(failures)} FAILURE(S): {failures}")
        sys.exit(1)
    print("ALL PASSED — schema conforms to doc 05 §4")


asyncio.run(main())
