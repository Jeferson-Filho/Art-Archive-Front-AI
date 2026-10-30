"""
Acceptance tests for doc 99, Phase 3 — the two Insight Card endpoints
(doc 07, §4; doc 06, §2, §3, §7). The fake Harvard records carry no image,
so generation stops at the pipeline's first step (doc 09, §4) and never
reaches Azure OpenAI: every generated block comes back empty.

Runs in-process against the real database named by DATABASE_URL, with the
Harvard client replaced by a fake. That is what makes the failure paths
reachable: a Harvard outage (502) and the guarantee that an already-persisted
block never reaches Harvard at all (RNF-001).

    PYTHONPATH=. python tests/test_insight_card_endpoints.py

Seeded rows use negative artwork IDs, which Harvard never issues, and are
deleted at the end.
"""

import asyncio
import sys

from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.config import get_settings
from app.db.base import get_session
from app.integrations import harvard
from app.main import app

PERSISTED = -100  # historical_context persisted with two sources; comparative_analysis missing
EXPIRED = -200  # historical_context persisted but soft-deleted: must read as missing
RETIRED_AND_ACTIVE = -300  # a retired row beside a fresh active one (doc 05 §6, Decision 12)
EXISTING = 299843  # exists in Harvard, nothing persisted
MISSING = 404404  # does not exist in Harvard
HARVARD_DOWN = 502502  # Harvard fails while checking it

failures: list[str] = []
harvard_calls: list[int] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + (f"  {detail}" if detail and not ok else ""))
    if not ok:
        failures.append(name)


async def fake_get_object(artwork_id: int) -> dict | None:
    harvard_calls.append(artwork_id)
    if artwork_id == HARVARD_DOWN:
        raise harvard.HarvardUnavailableError("HTTP 503")
    if artwork_id == MISSING:
        return None
    return {"objectid": artwork_id, "title": "Fake artwork"}


async def run_sql(*statements: str) -> None:
    # A dedicated engine, so the seeding loop never shares connections with the app's
    engine = create_async_engine(get_settings().database_url)
    async with engine.begin() as conn:
        for statement in statements:
            await conn.execute(text(statement))
    await engine.dispose()


SEEDED = f"({PERSISTED}, {EXPIRED}, {RETIRED_AND_ACTIVE})"


def insert_row(artwork_id: int, historical: str, expired: bool = False) -> str:
    return (
        "INSERT INTO artwork_ai_content (artwork_id, historical_context, historical_context_prompt_version, "
        f"historical_context_generated_at, expired_at) "
        f"VALUES ({artwork_id}, '{historical}', 'v1', now(), {'now()' if expired else 'NULL'})"
    )


def insert_sources(artwork_id: int, *urls: str, of_retired: bool = False) -> str:
    # Sources attach to a specific row through content_id (doc 05 §6, Decision 12)
    row = f"(SELECT id FROM artwork_ai_content WHERE artwork_id = {artwork_id} AND expired_at IS {'NOT ' if of_retired else ''}NULL)"
    values = ", ".join(
        f"({row}, 'historical_context', '{url}', now() - interval '{len(urls) - i} minute')" for i, url in enumerate(urls)
    )
    return f"INSERT INTO artwork_content_sources (content_id, block_type, url, created_at) VALUES {values}"


def seed() -> None:
    asyncio.run(
        run_sql(
            f"DELETE FROM artwork_ai_content WHERE artwork_id IN {SEEDED}",
            insert_row(PERSISTED, "Persisted context."),
            insert_sources(PERSISTED, "https://example.org/a", "https://example.org/b"),
            insert_row(EXPIRED, "Retired.", expired=True),
            insert_row(RETIRED_AND_ACTIVE, "Old text.", expired=True),
            insert_sources(RETIRED_AND_ACTIVE, "https://example.org/old", of_retired=True),
            insert_row(RETIRED_AND_ACTIVE, "Current text."),
            insert_sources(RETIRED_AND_ACTIVE, "https://example.org/current"),
        )
    )


def cleanup() -> None:
    asyncio.run(run_sql(f"DELETE FROM artwork_ai_content WHERE artwork_id IN {SEEDED}"))


async def unreadable_session():
    """A session on a closed port: the driver raises its real connection errors,
    which are what the persistence module must recognise (doc 06, §11 item 2)."""
    engine = create_async_engine("postgresql+asyncpg://nobody:nothing@127.0.0.1:1/none", connect_args={"timeout": 3})
    async with async_sessionmaker(engine)() as session:
        yield session
    await engine.dispose()


def assert_envelope(name: str, response, status: int, code: str) -> None:
    body = response.json()
    check(f"{name} -> {status}", response.status_code == status, f"got {response.status_code}")
    check(
        f"{name} -> envelope with code {code}",
        isinstance(body.get("error"), dict) and body["error"].get("code") == code and "message" in body["error"],
        f"got {body}",
    )


def run(client: TestClient) -> None:
    print("\nResponse shape (doc 07 §4) — artwork exists, nothing persisted")
    r = client.get(f"/artworks/{EXISTING}/historical-context")
    check("historical-context -> 200", r.status_code == 200)
    check(
        "historical-context fields exactly as doc 07",
        r.json() == {"artwork_id": EXISTING, "historical_context": "", "historical_context_sources": []},
        f"got {r.json()}",
    )
    r = client.get(f"/artworks/{EXISTING}/comparative-analysis")
    check("comparative-analysis -> 200", r.status_code == 200)
    check(
        "comparative-analysis fields exactly as doc 07",
        r.json() == {"artwork_id": EXISTING, "comparative_analysis": "", "comparative_analysis_sources": []},
        f"got {r.json()}",
    )

    print("\nPersisted block served from the database (RF-001, RNF-001)")
    harvard_calls.clear()
    r = client.get(f"/artworks/{PERSISTED}/historical-context")
    body = r.json()
    check("200 with the persisted text", r.status_code == 200 and body["historical_context"] == "Persisted context.")
    check(
        "sources returned in insertion order",
        body["historical_context_sources"] == ["https://example.org/a", "https://example.org/b"],
        f"got {body['historical_context_sources']}",
    )
    check("Harvard never consulted for a persisted block", harvard_calls == [], f"calls: {harvard_calls}")

    print("\nBlocks are independent (RF-001) — same artwork, the other block is missing")
    harvard_calls.clear()
    r = client.get(f"/artworks/{PERSISTED}/comparative-analysis")
    check("missing block is not served from the other column", r.json()["comparative_analysis"] == "")
    check("missing block goes on to check Harvard", harvard_calls == [PERSISTED], f"calls: {harvard_calls}")

    print("\nSoft-deleted row reads as missing (doc 05 §8)")
    harvard_calls.clear()
    r = client.get(f"/artworks/{EXPIRED}/historical-context")
    check("expired content is not returned", r.status_code == 200 and r.json()["historical_context"] == "")
    check("treated as missing, so Harvard is checked", harvard_calls == [EXPIRED], f"calls: {harvard_calls}")

    print("\nRetired row beside an active one (doc 05 §6, Decision 12)")
    harvard_calls.clear()
    r = client.get(f"/artworks/{RETIRED_AND_ACTIVE}/historical-context")
    body = r.json()
    check("the active row's text is served", r.status_code == 200 and body["historical_context"] == "Current text.")
    check(
        "only the active row's sources, never the retired row's",
        body["historical_context_sources"] == ["https://example.org/current"],
        f"got {body['historical_context_sources']}",
    )
    check("Harvard never consulted", harvard_calls == [], f"calls: {harvard_calls}")

    print("\nDatabase unreadable — treated as a missing block (doc 06 §11 item 2)")
    app.dependency_overrides[get_session] = unreadable_session
    try:
        for block in ("historical-context", "comparative-analysis"):
            harvard_calls.clear()
            r = client.get(f"/artworks/{EXISTING}/{block}")
            check(f"{block}: 200, not 500", r.status_code == 200, f"got {r.status_code} {r.text}")
            check(f"{block}: proceeds to the existence check", harvard_calls == [EXISTING], f"calls: {harvard_calls}")
        assert_envelope(
            "nonexistent artwork still 404 while the database is down",
            client.get(f"/artworks/{MISSING}/historical-context"),
            404,
            "ARTWORK_NOT_FOUND",
        )
    finally:
        app.dependency_overrides.pop(get_session, None)

    print("\nError catalog (doc 07 §6) — standard envelope")
    for block in ("historical-context", "comparative-analysis"):
        assert_envelope(f"{block}: nonexistent artwork", client.get(f"/artworks/{MISSING}/{block}"), 404, "ARTWORK_NOT_FOUND")
        assert_envelope(f"{block}: Harvard down", client.get(f"/artworks/{HARVARD_DOWN}/{block}"), 502, "HARVARD_API_ERROR")
        assert_envelope(f"{block}: non-integer id", client.get(f"/artworks/abc/{block}"), 400, "VALIDATION_ERROR")

    print("\nFramework errors also use the envelope")
    assert_envelope("unknown route", client.get("/does-not-exist"), 404, "NOT_FOUND")
    assert_envelope("wrong method", client.post(f"/artworks/{EXISTING}/historical-context"), 405, "METHOD_NOT_ALLOWED")

    print("\nCORS (doc 07 §1)")
    origin = get_settings().frontend_origin
    r = client.options(
        f"/artworks/{EXISTING}/historical-context",
        headers={"Origin": origin, "Access-Control-Request-Method": "GET"},
    )
    check("front-end origin allowed", r.headers.get("access-control-allow-origin") == origin)

    print("\nOpenAPI (/docs) reflects the contract")
    paths = client.get("/openapi.json").json()["paths"]
    operation = paths["/artworks/{artwork_id}/historical-context"]["get"]
    check("documents 400, 404, 502, 504", {"400", "404", "502", "504"} <= set(operation["responses"]))
    check("no phantom 422 anywhere", all("422" not in op["responses"] for item in paths.values() for op in item.values()))
    check("alt-text endpoint absent (deferred, doc 99 §2.2)", "/artworks/{artwork_id}/alt-text" not in paths)


def main() -> None:
    harvard.get_object = fake_get_object  # the persistence module resolves it at call time
    seed()
    try:
        with TestClient(app) as client:
            run(client)
    finally:
        cleanup()

    print()
    if failures:
        print(f"{len(failures)} FAILURE(S): {failures}")
        sys.exit(1)
    print("ALL PASSED — Phase 3 acceptance criteria met")


main()
