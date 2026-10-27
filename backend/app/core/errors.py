"""
Standard error envelope and error catalog (doc 07, §1 and §6).

Every error the API returns leaves in the same shape, whether an endpoint
raised it or the framework did:

    {"error": {"code": "STRING_CODE", "message": "Human-readable description"}}

Framework-level errors (malformed path parameters, unknown routes, wrong
methods, unhandled exceptions) are mapped onto that envelope too — author
decision of 2026-10-27, recorded in doc 07 (§6).
"""

import logging
from http import HTTPStatus

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger(__name__)


class ErrorBody(BaseModel):
    code: str
    message: str


class ErrorResponse(BaseModel):
    """Standard error envelope (doc 07, §1). Used to document error responses in OpenAPI."""

    error: ErrorBody


class APIError(Exception):
    """An error from the catalog of doc 07 (§6), rendered in the standard envelope."""

    def __init__(self, status_code: int, code: str, message: str) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message


def error_response(status_code: int, code: str, message: str, headers: dict | None = None) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={"error": {"code": code, "message": message}},
        headers=headers,
    )


def artwork_not_found(artwork_id: int) -> APIError:
    return APIError(404, "ARTWORK_NOT_FOUND", f"Artwork {artwork_id} does not exist in the Harvard Art Museums API.")


def harvard_api_error() -> APIError:
    return APIError(502, "HARVARD_API_ERROR", "The Harvard Art Museums API returned an error or a non-JSON response.")


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(APIError)
    async def handle_api_error(_: Request, exc: APIError) -> JSONResponse:
        return error_response(exc.status_code, exc.code, exc.message)

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(_: Request, exc: RequestValidationError) -> JSONResponse:
        # 400 VALIDATION_ERROR instead of FastAPI's default 422, whose body
        # would break the envelope. The offending value is not echoed back.
        errors = exc.errors()
        first = errors[0] if errors else {}
        field = ".".join(str(part) for part in first.get("loc", ()) if part not in ("path", "query", "body"))
        reason = first.get("msg", "invalid input")
        message = f"Invalid value for '{field}': {reason}." if field else "Invalid request."
        return error_response(400, "VALIDATION_ERROR", message)

    @app.exception_handler(StarletteHTTPException)
    async def handle_http_exception(_: Request, exc: StarletteHTTPException) -> JSONResponse:
        # Raised by the framework itself (unknown route, wrong method). The code
        # is the HTTP reason phrase: NOT_FOUND, METHOD_NOT_ALLOWED.
        phrase = HTTPStatus(exc.status_code).phrase
        code = phrase.upper().replace(" ", "_")
        return error_response(exc.status_code, code, f"{phrase}.", headers=getattr(exc, "headers", None))

    @app.exception_handler(Exception)
    async def handle_unexpected_error(_: Request, exc: Exception) -> JSONResponse:
        logger.exception("Unhandled error while serving a request")
        return error_response(500, "INTERNAL_ERROR", "An unexpected error occurred.")
