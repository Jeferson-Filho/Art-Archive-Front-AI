"""
Acceptance tests for the two Insight Card blocks (doc 07 v2.4, §4; doc 06
v2.4, §2, §3, §7): a GET that only reads, and a POST that generates from the
image the front-end sends (doc 99, Decision 11).

Runs in-process against the real database named by DATABASE_URL, with the
Harvard client and the AI Pipeline replaced by fakes, so nothing reaches
Harvard or Azure OpenAI. That is what makes the failure paths reachable: a
Harvard outage (502), a generation timeout (504), and the guarantee that a
persisted block never reaches Harvard or the pipeline at all (RNF-001).

    PYTHONPATH=. python tests/test_insight_card_endpoints.py

Seeded and generated rows use negative artwork IDs, which Harvard never
issues, and are deleted at the end.
"""

import asyncio
import base64
import sys

from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.config import get_settings
from app.db.base import get_session
from app.integrations import harvard
from app.main import app
from app.persistence import insight_card
from app.pipeline.generation import LLMProviderError, LLMTimeoutError, TextBlockResult

PERSISTED = -100  # historical_context persisted with two sources; comparative_analysis missing
EXPIRED = -200  # historical_context persisted but soft-deleted: must read as missing
RETIRED_AND_ACTIVE = -300  # a retired row beside a fresh active one (doc 05 §6, Decision 12)
GENERATED = -400  # nothing persisted; the fake pipeline returns content
EMPTY = -500  # nothing persisted; the fake pipeline returns an empty block
DB_DOWN = -600  # generated while the database is unreadable: must not be persisted
TIMEOUT = -700  # the fake pipeline times out
PROVIDER_ERROR = -800  # the fake pipeline fails with a provider error
EXISTING = 299843  # exists in Harvard, nothing persisted — only read, never generated here
MISSING = 404404  # does not exist in Harvard
HARVARD_DOWN = 502502  # Harvard fails while checking it

JPEG = b"\xff\xd8\xff\xe0" + b"\x00" * 64
PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 64
VALID_IMAGE = "data:image/jpeg;base64," + base64.b64encode(JPEG).decode()

failures: list[str] = []
harvard_calls: list[int] = []
pipeline_calls: list[tuple[int, str]] = []


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
    return {"objectid": artwork_id, "title": str(artwork_id)}


def fake_generator(block: str):
    """Stands in for the AI Pipeline. The artwork ID travels in the title the fake Harvard record carries."""

    async def generate(image: str, metadata, timeout: float) -> TextBlockResult:
        artwork_id = int(metadata.title)
        pipeline_calls.append((artwork_id, image))
        if artwork_id == TIMEOUT:
            raise LLMTimeoutError("fake timeout")
        if artwork_id == PROVIDER_ERROR:
            raise LLMProviderError("HTTP 400 content_policy_violation")
        if artwork_id == EMPTY:
            return TextBlockResult(text="", sources=[], prompt_version="v1")
        return TextBlockResult(text=f"Generated {block}.", sources=[f"https://example.org/{block}"], prompt_version="v1")

    return generate


async def run_sql(*statements: str) -> list:
    # A dedicated engine, so the seeding loop never shares connections with the app's
    engine = create_async_engine(get_settings().database_url)
    results = []
    async with engine.begin() as conn:
        for statement in statements:
            result = await conn.execute(text(statement))
            results.append(result.fetchall() if result.returns_rows else None)
    await engine.dispose()
    return results


TEST_IDS = f"({PERSISTED}, {EXPIRED}, {RETIRED_AND_ACTIVE}, {GENERATED}, {EMPTY}, {DB_DOWN}, {TIMEOUT}, {PROVIDER_ERROR})"


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
            f"DELETE FROM artwork_ai_content WHERE artwork_id IN {TEST_IDS}",
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
    asyncio.run(run_sql(f"DELETE FROM artwork_ai_content WHERE artwork_id IN {TEST_IDS}"))


def active_rows(artwork_id: int) -> int:
    rows = asyncio.run(
        run_sql(f"SELECT count(*) FROM artwork_ai_content WHERE artwork_id = {artwork_id} AND expired_at IS NULL")
    )[0]
    return rows[0][0]


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


def post(client: TestClient, artwork_id, block: str, image: str | None = VALID_IMAGE):
    return client.post(f"/artworks/{artwork_id}/{block}", json=None if image is None else {"image": image})


def run_reads(client: TestClient) -> None:
    print("\nGET — missing block reads as null (doc 07 §4), without Harvard or the pipeline")
    harvard_calls.clear()
    pipeline_calls.clear()
    r = client.get(f"/artworks/{EXISTING}/historical-context")
    check("historical-context -> 200", r.status_code == 200)
    check(
        "historical-context fields exactly as doc 07",
        r.json() == {"artwork_id": EXISTING, "historical_context": None, "historical_context_sources": []},
        f"got {r.json()}",
    )
    r = client.get(f"/artworks/{EXISTING}/comparative-analysis")
    check("comparative-analysis -> 200", r.status_code == 200)
    check(
        "comparative-analysis fields exactly as doc 07",
        r.json() == {"artwork_id": EXISTING, "comparative_analysis": None, "comparative_analysis_sources": []},
        f"got {r.json()}",
    )
    check("GET never consults Harvard", harvard_calls == [], f"calls: {harvard_calls}")
    check("GET never calls the pipeline", pipeline_calls == [], f"calls: {len(pipeline_calls)}")

    print("\nGET — persisted block served from the database (RF-001, RNF-001)")
    r = client.get(f"/artworks/{PERSISTED}/historical-context")
    body = r.json()
    check("200 with the persisted text", r.status_code == 200 and body["historical_context"] == "Persisted context.")
    check(
        "sources returned in insertion order",
        body["historical_context_sources"] == ["https://example.org/a", "https://example.org/b"],
        f"got {body['historical_context_sources']}",
    )

    print("\nGET — blocks are independent (RF-001): same artwork, the other block is missing")
    r = client.get(f"/artworks/{PERSISTED}/comparative-analysis")
    check("missing block reads as null, not the other column", r.json()["comparative_analysis"] is None)

    print("\nGET — soft-deleted row reads as missing (doc 05 §8)")
    r = client.get(f"/artworks/{EXPIRED}/historical-context")
    check("expired content is not returned", r.status_code == 200 and r.json()["historical_context"] is None)

    print("\nGET — retired row beside an active one (doc 05 §6, Decision 12)")
    r = client.get(f"/artworks/{RETIRED_AND_ACTIVE}/historical-context")
    body = r.json()
    check("the active row's text is served", r.status_code == 200 and body["historical_context"] == "Current text.")
    check(
        "only the active row's sources, never the retired row's",
        body["historical_context_sources"] == ["https://example.org/current"],
        f"got {body['historical_context_sources']}",
    )


def run_generation(client: TestClient) -> None:
    print("\nPOST — generates, persists and returns the block (doc 06 §2, RF-004)")
    for block, field in (("historical-context", "historical_context"), ("comparative-analysis", "comparative_analysis")):
        pipeline_calls.clear()
        r = post(client, GENERATED, block)
        body = r.json()
        check(f"{block}: 200 with the generated text", r.status_code == 200 and body[field] == f"Generated {field}.")
        check(f"{block}: the received image reaches the pipeline", pipeline_calls == [(GENERATED, VALID_IMAGE)])
        r = client.get(f"/artworks/{GENERATED}/{block}")
        check(f"{block}: the next GET serves it", r.json()[field] == f"Generated {field}.", f"got {r.json()}")
        check(
            f"{block}: with its sources",
            r.json()[f"{field}_sources"] == [f"https://example.org/{field}"],
            f"got {r.json()}",
        )
    check("both blocks share one active row (doc 06 §6)", active_rows(GENERATED) == 1)

    print("\nPOST — a block persisted in the meantime is returned, the image ignored (RF-001)")
    harvard_calls.clear()
    pipeline_calls.clear()
    r = post(client, PERSISTED, "historical-context")
    check("200 with the persisted text", r.status_code == 200 and r.json()["historical_context"] == "Persisted context.")
    check("Harvard never consulted", harvard_calls == [], f"calls: {harvard_calls}")
    check("pipeline never called", pipeline_calls == [], f"calls: {len(pipeline_calls)}")

    print("\nPOST — an empty block is returned as \"\" and not persisted (RF-002 scenario 3)")
    r = post(client, EMPTY, "historical-context")
    check("200 with an empty text", r.status_code == 200 and r.json()["historical_context"] == "")
    check("nothing persisted", active_rows(EMPTY) == 0)

    print("\nPOST — a provider error is an empty block, not an error (RF-007 scenario 1)")
    r = post(client, PROVIDER_ERROR, "comparative-analysis")
    check("200 with an empty text", r.status_code == 200 and r.json()["comparative_analysis"] == "")

    print("\nPOST — database unreadable: generates, returns, persists nothing (doc 06 §11 item 2)")
    app.dependency_overrides[get_session] = unreadable_session
    try:
        r = client.get(f"/artworks/{PERSISTED}/historical-context")
        check("GET reads as null, not 500", r.status_code == 200 and r.json()["historical_context"] is None, f"got {r.text}")
        r = post(client, DB_DOWN, "historical-context")
        check("POST: 200 with the generated text", r.status_code == 200 and r.json()["historical_context"] == "Generated historical_context.")
    finally:
        app.dependency_overrides.pop(get_session, None)
    check("POST: nothing persisted", active_rows(DB_DOWN) == 0)

    print("\nPOST — error catalog (doc 07 §6), standard envelope")
    assert_envelope("timeout", post(client, TIMEOUT, "historical-context"), 504, "GENERATION_TIMEOUT")
    for block in ("historical-context", "comparative-analysis"):
        assert_envelope(f"{block}: nonexistent artwork", post(client, MISSING, block), 404, "ARTWORK_NOT_FOUND")
        assert_envelope(f"{block}: Harvard down", post(client, HARVARD_DOWN, block), 502, "HARVARD_API_ERROR")
        assert_envelope(f"{block}: non-integer id", post(client, "abc", block), 400, "VALIDATION_ERROR")
        assert_envelope(f"{block}: GET non-integer id", client.get(f"/artworks/abc/{block}"), 400, "VALIDATION_ERROR")


def run_validation(client: TestClient) -> None:
    print("\nPOST — the image is validated before anything else (doc 07 §4)")
    invalid = {
        "no body": None,
        "not a data URL": "https://nrs.harvard.edu/urn-3:HUAM:1",
        "unsupported type": "data:image/gif;base64," + base64.b64encode(b"GIF89a" + b"\x00" * 16).decode(),
        "declared PNG, JPEG bytes": "data:image/png;base64," + base64.b64encode(JPEG).decode(),
        "not base64": "data:image/jpeg;base64,!!!not-base64!!!",
        "over 1.5 MB": "data:image/jpeg;base64," + base64.b64encode(b"\xff\xd8\xff" + b"\x00" * 1_600_000).decode(),
    }
    pipeline_calls.clear()
    harvard_calls.clear()
    for name, image in invalid.items():
        assert_envelope(name, post(client, GENERATED + 1, "historical-context", image), 400, "VALIDATION_ERROR")
    check("an invalid image never reaches Harvard or the pipeline", pipeline_calls == [] and harvard_calls == [])
    r = post(client, EMPTY, "historical-context", "data:image/png;base64," + base64.b64encode(PNG).decode())
    check("a PNG is accepted", r.status_code == 200, f"got {r.status_code}")


def run_framework(client: TestClient) -> None:
    print("\nFramework errors also use the envelope")
    assert_envelope("unknown route", client.get("/does-not-exist"), 404, "NOT_FOUND")
    assert_envelope("wrong method", client.put(f"/artworks/{EXISTING}/historical-context"), 405, "METHOD_NOT_ALLOWED")

    print("\nCORS (doc 07 §1)")
    origin = get_settings().frontend_origin
    r = client.options(
        f"/artworks/{EXISTING}/historical-context",
        headers={"Origin": origin, "Access-Control-Request-Method": "POST", "Access-Control-Request-Headers": "content-type"},
    )
    check("front-end origin allowed to POST JSON", r.headers.get("access-control-allow-origin") == origin)

    print("\nOpenAPI (/docs) reflects the contract")
    paths = client.get("/openapi.json").json()["paths"]
    operations = paths["/artworks/{artwork_id}/historical-context"]
    check("GET documents 400", "400" in operations["get"]["responses"])
    check("POST documents 400, 404, 502, 504", {"400", "404", "502", "504"} <= set(operations["post"]["responses"]))
    check("no phantom 422 anywhere", all("422" not in op["responses"] for item in paths.values() for op in item.values()))
    check("alt-text endpoint absent (deferred, doc 99 §2.2)", "/artworks/{artwork_id}/alt-text" not in paths)


def main() -> None:
    harvard.get_object = fake_get_object  # the persistence module resolves it at call time
    insight_card.GENERATORS.update(
        historical_context=fake_generator("historical_context"),
        comparative_analysis=fake_generator("comparative_analysis"),
    )
    seed()
    try:
        with TestClient(app) as client:
            run_reads(client)
            run_generation(client)
            run_validation(client)
            run_framework(client)
    finally:
        cleanup()

    print()
    if failures:
        print(f"{len(failures)} FAILURE(S): {failures}")
        sys.exit(1)
    print("ALL PASSED — Insight Card GET/POST contract met (doc 07 v2.4)")


main()
