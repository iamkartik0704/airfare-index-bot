"""Root of the SAFAR exception hierarchy.

Subsystem-specific errors live next to their subsystem and subclass these:

* ``packages.scraping.core.exceptions`` — network, timeout, blocked, rate-limited,
  robots-disallowed, parse errors.
* ``packages.data_pipeline.exceptions`` — validation / normalization errors.
* ``packages.index_engine.exceptions`` — index calculation errors.

Every error carries a ``context`` mapping (job_id, source, route, …) so it can
be logged and persisted on the job without string parsing.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any


class SafarError(Exception):
    """Base class for all expected, typed failures in SAFAR."""

    #: Whether an orchestrator may retry the operation that raised this error.
    retryable: bool = False
    #: Stable machine-readable error code (persisted on jobs, returned by the API).
    code: str = "safar_error"

    def __init__(self, message: str, **context: Any) -> None:
        super().__init__(message)
        self.message = message
        self.context: Mapping[str, Any] = context

    def __str__(self) -> str:
        if not self.context:
            return self.message
        ctx = ", ".join(f"{k}={v}" for k, v in sorted(self.context.items()))
        return f"{self.message} ({ctx})"


class ConfigurationError(SafarError):
    code = "configuration_error"


class NotFoundError(SafarError):
    code = "not_found"


class ConflictError(SafarError):
    code = "conflict"


class PersistenceError(SafarError):
    code = "database_error"
    retryable = True
