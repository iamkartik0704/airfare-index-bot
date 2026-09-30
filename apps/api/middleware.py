"""Request-ID propagation and structured access logging."""

from __future__ import annotations

import time
import uuid
from collections.abc import Awaitable, Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from packages.observability.logging import bind_context, get_logger

log = get_logger("safar.api.access")


class RequestContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        incoming = request.headers.get("x-request-id", "")
        request_id = incoming if 0 < len(incoming) <= 64 else uuid.uuid4().hex
        request.state.request_id = request_id
        started = time.perf_counter()
        with bind_context(request_id=request_id):
            response = await call_next(request)
            log.info(
                "http.request",
                method=request.method,
                path=request.url.path,
                status=response.status_code,
                duration_ms=int((time.perf_counter() - started) * 1000),
            )
        response.headers["X-Request-ID"] = request_id
        return response
