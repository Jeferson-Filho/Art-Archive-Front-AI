"""
Art Archive AI — single backend service (doc 04 §1).

Replaces the Flask proxy (`proxy/proxy.py`), absorbing the Harvard Art
Museums API proxy (doc 04 §4). AI pipeline, persistence, and authentication
modules are added in later phases (doc 99, Phases 4-5, 7).
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.harvard_proxy import router as harvard_proxy_router
from app.core.config import get_settings

app = FastAPI(title="Art Archive AI — Backend")

settings = get_settings()

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(harvard_proxy_router)


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}
