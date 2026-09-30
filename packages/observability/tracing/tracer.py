"""Lightweight spans: timed, logged units of work.

A deliberate, dependency-free alternative to a full OpenTelemetry SDK for the
prototype (doc 16 target A). Each span logs ``span.finished`` with its
duration and outcome, and binds ``span`` into the log context for nested
records. Swapping in OpenTelemetry later only touches this module.
"""

from __future__ import annotations

import time
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

from packages.observability.logging.logger import bind_context, get_logger

_log = get_logger("safar.span")


@contextmanager
def span(name: str, **attributes: Any) -> Iterator[dict[str, Any]]:
    """Time a block. Callers may add result attributes to the yielded dict."""
    started = time.perf_counter()
    result: dict[str, Any] = {}
    with bind_context(span=name):
        try:
            yield result
        except BaseException as exc:
            _log.warning(
                "span.failed",
                duration_ms=int((time.perf_counter() - started) * 1000),
                error_type=exc.__class__.__name__,
                **attributes,
                **result,
            )
            raise
        _log.info(
            "span.finished",
            duration_ms=int((time.perf_counter() - started) * 1000),
            **attributes,
            **result,
        )
