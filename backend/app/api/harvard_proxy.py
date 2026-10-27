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

router = APIRouter(prefix="/proxy", tags=["harvard-proxy"])


@router.get("/{path:path}")
async def proxy_harvard(path: str, request: Request) -> JSONResponse:
    settings = get_settings()

    params = dict(request.query_params)
    params["apikey"] = settings.harvard_api_key

    url = f"{settings.harvard_api_base_url}/{path}"

    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            response = await client.get(url, params=params)
        except httpx.HTTPError:
            return _harvard_api_error()

    if response.status_code != 200:
        return _harvard_api_error()

    try:
        body = response.json()
    except ValueError:
        return _harvard_api_error()

    if isinstance(body, dict) and "info" in body and isinstance(body["info"], dict):
        body["info"].pop("next", None)
        body["info"].pop("prev", None)

    return JSONResponse(content=body)


def _harvard_api_error() -> JSONResponse:
    """Standard error envelope (doc 07 §1), code `HARVARD_API_ERROR` (doc 07 §3/§6)."""
    return JSONResponse(
        status_code=502,
        content={
            "error": {
                "code": "HARVARD_API_ERROR",
                "message": "The Harvard Art Museums API returned an error or a non-JSON response.",
            }
        },
    )
