"""Scraping error hierarchy (docs 04, 10, 15).

The orchestrator decides what to do from the *type* of error, never from the
message: retryable errors re-queue the job with backoff, policy errors skip it,
parser errors send it to the dead-letter set for a developer.
"""

from __future__ import annotations

from packages.domain.exceptions import SafarError


class ScrapingError(SafarError):
    code = "scraping_error"


class NetworkError(ScrapingError):
    """Connection reset, DNS failure, TLS error."""

    code = "network_error"
    retryable = True


class FetchTimeoutError(NetworkError):
    code = "timeout"


class HttpStatusError(ScrapingError):
    """Unexpected HTTP status. 5xx are retryable, 4xx are not."""

    code = "http_status"

    def __init__(self, message: str, *, status: int, **context: object) -> None:
        super().__init__(message, status=status, **context)
        self.status = status
        self.retryable = status >= 500


class RateLimitedError(ScrapingError):
    """HTTP 429 — back off for ``retry_after_s`` (doc 10: pause that domain)."""

    code = "rate_limited"
    retryable = True
    retry_after_s: float | None

    def __init__(self, message: str, *, retry_after_s: float | None = None, **context: object):
        super().__init__(message, retry_after_s=retry_after_s, **context)
        self.retry_after_s = retry_after_s


class SourceBlockedError(ScrapingError):
    """A challenge/CAPTCHA/403 page. Never bypassed: the source is flagged BLOCKED (doc 15)."""

    code = "source_blocked"


class RobotsDisallowedError(ScrapingError):
    """robots.txt disallows the URL, or robots.txt was unavailable and policy is fail-closed."""

    code = "robots_disallowed"


class CircuitOpenError(ScrapingError):
    """The source's circuit breaker is open after repeated failures (doc 04)."""

    code = "circuit_open"


class SourceDisabledError(ScrapingError):
    code = "source_disabled"


class ParseError(ScrapingError):
    """The response did not contain a mandatory field / expected structure (doc 05)."""

    code = "parse_error"


__all__ = [
    "CircuitOpenError",
    "FetchTimeoutError",
    "HttpStatusError",
    "NetworkError",
    "ParseError",
    "RateLimitedError",
    "RobotsDisallowedError",
    "ScrapingError",
    "SourceBlockedError",
    "SourceDisabledError",
]
