"""
Harvard Art Museums API client for the On-Demand Persistence module, which
must confirm an artwork exists before generating anything for it (doc 07, §4)
and needs its metadata to do so (doc 06, §7).

The Harvard Proxy endpoint (app/api/harvard_proxy.py) does not use this
client: its contract is to pass Harvard's response through unchanged
(doc 07, §3), whereas this module interprets it.
"""

import httpx

from app.core.config import get_settings

HARVARD_TIMEOUT_SECONDS = 10.0


class HarvardUnavailableError(Exception):
    """Harvard could not be reached or answered with an error — distinct from 'artwork does not exist'.

    Messages never carry the request URL, which holds the API key (RNF-005).
    """


async def get_object(artwork_id: int) -> dict | None:
    """Return the artwork's record, or None when Harvard reports it does not exist.

    Harvard answers a nonexistent object with HTTP 200 and the body
    `{"error": "Not found"}`, not with a 404 (observed 2026-10-27), so absence
    is read from the body. A 404 status is treated the same way, in case that
    behaviour ever changes.
    """
    settings = get_settings()
    url = f"{settings.harvard_api_base_url}/object/{artwork_id}"

    try:
        async with httpx.AsyncClient(timeout=HARVARD_TIMEOUT_SECONDS) as client:
            response = await client.get(url, params={"apikey": settings.harvard_api_key})
    except httpx.HTTPError as exc:
        raise HarvardUnavailableError(type(exc).__name__) from None

    if response.status_code == 404:
        return None
    if response.status_code != 200:
        raise HarvardUnavailableError(f"HTTP {response.status_code}")

    try:
        body = response.json()
    except ValueError:
        raise HarvardUnavailableError("non-JSON response") from None

    if isinstance(body, dict) and "objectid" in body:
        return body
    if isinstance(body, dict) and body.get("error") == "Not found":
        return None
    raise HarvardUnavailableError("unexpected response shape")
