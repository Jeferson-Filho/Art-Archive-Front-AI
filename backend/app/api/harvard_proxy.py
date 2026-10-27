"""
Harvard Proxy module (doc 04 §4; doc 07 §3).

Reimplements, at contract parity, the single route the original Flask proxy
(`proxy/proxy.py`) exposed: `GET /proxy/<path>`. See doc 99 (Phase 1) for the
exact contract preserved here —

1. Every query parameter is forwarded to the Harvard Art Museums API.
2. The `apikey` parameter is injected server-side (RNF-005) — never by the client.
3. `info.next` and `info.prev` are stripped from the response body when present.
4. A non-200 or non-JSON response from Harvard is surfaced as `502 HARVARD_API_ERROR`.

No functionality beyond this is added — doc 00 (§3.3) forbids generalizing
beyond what the current specification (doc 07 §3) requires.
"""

import httpx
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from app.core.config import get_settings
from app.core.errors import ErrorResponse, harvard_api_error

router = APIRouter(prefix="/proxy", tags=["Harvard Proxy"])


@router.get(
    "/{path:path}",
    summary="Forward a request to the Harvard Art Museums API",
    responses={502: {"model": ErrorResponse, "description": "`HARVARD_API_ERROR`"}},
)
async def proxy_harvard(path: str, request: Request) -> JSONResponse:
    """Forwards `path` and every query parameter to Harvard, with the API key
    attached server-side; returns Harvard's body with `info.next`/`info.prev` removed."""
    settings = get_settings()

    params = dict(request.query_params)
    params["apikey"] = settings.harvard_api_key

    url = f"{settings.harvard_api_base_url}/{path}"

    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            response = await client.get(url, params=params)
        except httpx.HTTPError:
            raise harvard_api_error() from None

    if response.status_code != 200:
        raise harvard_api_error()

    try:
        body = response.json()
    except ValueError:
        raise harvard_api_error() from None

    if isinstance(body, dict) and "info" in body and isinstance(body["info"], dict):
        body["info"].pop("next", None)
        body["info"].pop("prev", None)

    return JSONResponse(content=body)
