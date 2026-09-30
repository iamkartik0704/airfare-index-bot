"""Source-side domain records (doc 05 ``metadata()``, doc 13 health)."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict

from packages.domain.enums import SourceKind, SourceStatus


class SourceMetadata(BaseModel):
    """What an adapter declares about its source (doc 05 contract item 1)."""

    model_config = ConfigDict(frozen=True)

    id: str
    name: str
    kind: SourceKind
    base_url: str
    carrier: str | None
    fetch_mode: str
    rate_limit_rpm: int
    max_concurrency: int
    crawl_delay_s: float
    purchase_windows: tuple[int, ...]
    parser_name: str
    parser_version: str
    capabilities: tuple[str, ...]
    is_synthetic: bool


class HealthCheckResult(BaseModel):
    """Outcome of an adapter's fast structural check (doc 05 contract item 4)."""

    model_config = ConfigDict(frozen=True)

    source_id: str
    ok: bool
    checked_at: datetime
    status_code: int | None = None
    latency_ms: int | None = None
    detail: str


class SourceHealthMetric(BaseModel):
    """Aggregated health of a source over a time window (doc 13)."""

    model_config = ConfigDict(frozen=True)

    source_id: str
    status: SourceStatus
    window_hours: int
    requests: int
    jobs_succeeded: int
    jobs_failed: int
    blocked: int
    rate_limited: int
    parse_errors: int
    robots_denied: int
    quotes_collected: int
    avg_latency_ms: float | None
    success_rate: float | None
    last_success_at: datetime | None
