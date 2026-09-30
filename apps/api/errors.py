"""Centralised exception → HTTP mapping with a structured error body (doc 11)."""

from __future__ import annotations

from collections.abc import Mapping

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from apps.api.dependencies.db import UnauthorizedError
from apps.api.schemas.common import ErrorBody, ErrorResponse
from packages.domain.exceptions import (
    ConfigurationError,
    ConflictError,
    NotFoundError,
    PersistenceError,
    SafarError,
)
from packages.index_engine.exceptions import InsufficientDataError
from packages.observability.logging import get_logger

log = get_logger("safar.api")

STATUS_BY_TYPE: list[tuple[type[SafarError], int]] = [
    (UnauthorizedError, 401),
    (NotFoundError, 404),
    (InsufficientDataError, 404),
    (ConflictError, 409),
    (ConfigurationError, 422),
    (PersistenceError, 503),
]


def _status_for(exc: SafarError) -> int:
    for exc_type, status in STATUS_BY_TYPE:
        if isinstance(exc, exc_type):
            return status
    return 500


def _body(
    request: Request, code: str, message: str, details: Mapping[str, object]
) -> dict[str, object]:
    request_id = getattr(request.state, "request_id", None)
    return ErrorResponse(
        error=ErrorBody(code=code, message=message, details=dict(details), request_id=request_id)
    ).model_dump()


def install_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(SafarError)
    async def _safar(request: Request, exc: SafarError) -> JSONResponse:
        status = _status_for(exc)
        if status >= 500:
            log.error("api.error", error_code=exc.code, error=str(exc), path=request.url.path)
        details = {k: str(v) for k, v in exc.context.items()}
        return JSONResponse(
            status_code=status, content=_body(request, exc.code, exc.message, details)
        )

    @app.exception_handler(RequestValidationError)
    async def _validation(request: Request, exc: RequestValidationError) -> JSONResponse:
        details = {"errors": [{"loc": list(e["loc"]), "msg": e["msg"]} for e in exc.errors()]}
        return JSONResponse(
            status_code=422, content=_body(request, "validation_error", "invalid request", details)
        )

    @app.exception_handler(StarletteHTTPException)
    async def _http(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        code = "not_found" if exc.status_code == 404 else f"http_{exc.status_code}"
        return JSONResponse(
            status_code=exc.status_code, content=_body(request, code, str(exc.detail), {})
        )
