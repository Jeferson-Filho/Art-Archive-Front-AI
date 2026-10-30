"""
Art Archive AI — single backend service (doc 04 §1).

Replaces the Flask proxy, absorbing the Harvard Art Museums API proxy
(doc 04 §4), and serves the Insight Card endpoints (doc 07 §4). The AI
pipeline and authentication arrive in later phases (doc 99, Phases 4-5, 7).

Interactive documentation is generated from this code at /docs (Swagger UI)
and /openapi.json. The source of truth for the contract remains doc 07.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi

from app.api.artworks import router as artworks_router
from app.api.harvard_proxy import router as harvard_proxy_router
from app.core.config import get_settings
from app.core.errors import register_error_handlers

app = FastAPI(
    title="Art Archive AI — Backend",
    version="0.3.0",
    description=(
        "Single backend service of Art Archive AI (doc 04 §1). Generated from the code; "
        "the source of truth for the contract is `documentation/specs/07-api-contract.md`.\n\n"
        "Every error is returned as `{\"error\": {\"code\": \"...\", \"message\": \"...\"}}` (doc 07 §1)."
    ),
)

settings = get_settings()

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

register_error_handlers(app)

app.include_router(harvard_proxy_router)
app.include_router(artworks_router)


@app.get("/health", tags=["Health"], summary="Liveness check")
async def health() -> dict:
    return {"status": "ok"}


def _openapi_without_422() -> dict:
    """Validation errors are returned as 400 VALIDATION_ERROR (app/core/errors.py),
    so the 422 FastAPI documents on every route by default never happens."""
    if app.openapi_schema:
        return app.openapi_schema

    schema = get_openapi(title=app.title, version=app.version, description=app.description, routes=app.routes)
    for path_item in schema.get("paths", {}).values():
        for operation in path_item.values():
            operation.get("responses", {}).pop("422", None)

    component_schemas = schema.get("components", {}).get("schemas", {})
    component_schemas.pop("HTTPValidationError", None)
    component_schemas.pop("ValidationError", None)

    app.openapi_schema = schema
    return schema


app.openapi = _openapi_without_422
