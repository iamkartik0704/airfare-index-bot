"""Structured JSON logging (doc 13 "Logging").

Every record carries ``timestamp``, ``level``, ``event`` and whatever context is
bound for the current task — ``job_id``, ``source``, ``route``,
``travel_date``, ``purchase_window``, ``request_id`` — via contextvars, so
concurrent jobs never mix their context.

    from packages.observability.logging import get_logger, bind_context
    log = get_logger(__name__)
    with bind_context(job_id=str(job.id), source=job.source_id):
        log.info("scrape.started")
"""

from __future__ import annotations

import logging
import sys
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

import structlog

_configured = False


def configure_logging(level: str = "INFO", json: bool = True) -> None:
    """Idempotent process-wide logging setup."""
    global _configured
    shared: list[structlog.types.Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]
    renderer: structlog.types.Processor = (
        structlog.processors.JSONRenderer() if json else structlog.dev.ConsoleRenderer()
    )
    structlog.configure(
        processors=[*shared, renderer],
        wrapper_class=structlog.make_filtering_bound_logger(logging.getLevelName(level.upper())),
        logger_factory=structlog.PrintLoggerFactory(file=sys.stderr),
        cache_logger_on_first_use=False,
    )
    # Route stdlib logging (uvicorn, alembic, apscheduler) through the same format.
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(
        structlog.stdlib.ProcessorFormatter(foreign_pre_chain=shared, processor=renderer)
    )
    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(level.upper())
    # Per-request transport chatter; SAFAR logs its own structured request events.
    for noisy in ("httpx", "httpcore", "apscheduler.executors.default"):
        logging.getLogger(noisy).setLevel(max(logging.WARNING, root.level))
    _configured = True


def get_logger(name: str | None = None) -> Any:
    return structlog.get_logger(name) if name else structlog.get_logger()


@contextmanager
def bind_context(**fields: Any) -> Iterator[None]:
    """Bind fields to every log line emitted in this task until the block exits."""
    clean = {k: (str(v) if v is not None else None) for k, v in fields.items()}
    tokens = structlog.contextvars.bind_contextvars(**clean)
    try:
        yield
    finally:
        structlog.contextvars.reset_contextvars(**tokens)
