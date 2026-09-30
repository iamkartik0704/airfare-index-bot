"""Classification of responses into success / rate-limited / blocked / error.

A block (CAPTCHA, bot challenge, 401/403) is *never* bypassed: the engine
raises ``SourceBlockedError``, the job is not retried, the source is flagged
``BLOCKED`` and the index engine imputes the missing cells (doc 15 §2).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime

from packages.scraping.core.exceptions import (
    HttpStatusError,
    RateLimitedError,
    SourceBlockedError,
)
from packages.scraping.core.fetchers.base import FetchResponse

# Markers that only appear on challenge/interstitial pages. Bare "captcha" is
# deliberately absent: normal pages embed reCAPTCHA for login forms.
CHALLENGE_MARKERS: tuple[str, ...] = (
    "verify you are human",
    "are you a robot",
    "unusual traffic from your",
    "cf-challenge",
    "cf-browser-verification",
    "_incapsula_resource",
    "px-captcha",
    "captcha-delivery.com",
    "pardon our interruption",
    "<title>access denied</title>",
    "<title>just a moment...</title>",
    "request blocked",
)


@dataclass(frozen=True)
class BlockVerdict:
    blocked: bool
    reason: str | None = None


def _looks_like_html(response: FetchResponse) -> bool:
    ctype = (response.content_type or "").lower()
    if "html" in ctype:
        return True
    return response.body[:64].lstrip().lower().startswith((b"<!doctype", b"<html"))


def detect_block(response: FetchResponse, extra_markers: tuple[str, ...] = ()) -> BlockVerdict:
    if response.status in (401, 403):
        return BlockVerdict(True, f"HTTP {response.status}")
    if _looks_like_html(response):
        lowered = response.text.lower()
        for marker in (*CHALLENGE_MARKERS, *extra_markers):
            if marker in lowered:
                return BlockVerdict(True, f"challenge marker '{marker}'")
    return BlockVerdict(False)


def _retry_after_seconds(value: str | None) -> float | None:
    if not value:
        return None
    try:
        return max(0.0, float(value))
    except ValueError:
        try:
            when = parsedate_to_datetime(value)
        except (TypeError, ValueError):
            return None
        return max(0.0, (when - datetime.now(UTC)).total_seconds())


def raise_for_response(
    response: FetchResponse, *, source_id: str, extra_markers: tuple[str, ...] = ()
) -> None:
    """Raise the typed error that describes a non-successful response."""
    ctx = {"source": source_id, "url": response.url}
    if response.status == 429:
        retry_after = _retry_after_seconds(
            next((v for k, v in response.headers.items() if k.lower() == "retry-after"), None)
        )
        raise RateLimitedError(
            "source rate-limited us (HTTP 429)", retry_after_s=retry_after, **ctx
        )
    verdict = detect_block(response, extra_markers)
    if verdict.blocked:
        raise SourceBlockedError(
            f"source presented a block: {verdict.reason}", status=response.status, **ctx
        )
    if response.status >= 400 or response.status < 100:
        raise HttpStatusError(f"unexpected HTTP {response.status}", status=response.status, **ctx)
