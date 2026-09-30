"""Fares, analytics, system, jobs, backtest and methodology schemas."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from pydantic import Field

from apps.api.schemas.common import ApiModel, DataOrigin
from packages.domain.enums import (
    AvailabilityStatus,
    Cabin,
    JobStatus,
    QualityFlag,
    SourceKind,
    SourceStatus,
    SweepStatus,
    SweepTrigger,
)

# ----------------------------------------------------------------------------- fares


class FareOut(ApiModel):
    id: int
    source_id: str
    route: str
    carrier_code: str
    flight_number: str
    fare_class: str
    fare_family: str | None
    cabin: Cabin
    observation_date: date
    observed_at: datetime
    travel_date: date
    purchase_window: int
    base_fare: Decimal | None
    taxes: Decimal | None
    airport_fees: Decimal | None
    convenience_fee: Decimal | None
    total_fare: Decimal | None
    availability: AvailabilityStatus
    seats_left: int | None
    stops: int | None
    quality_flag: QualityFlag
    quality_reasons: list[str]
    is_canonical: bool
    is_synthetic: bool


class FareLineage(ApiModel):
    fare: FareOut
    raw_payload: dict[str, Any]
    parser: str
    response_id: UUID
    response_url: str
    response_status: int
    response_sha256: str
    fetched_at: datetime
    job_id: UUID
    sweep_id: UUID


class FunnelOut(ApiModel):
    observation_date: date
    route: str | None
    raw: int
    normalized: int
    valid: int
    outliers: int
    duplicates: int
    invalid: int
    sold_out: int
    cancelled: int
    canonical: int


# ----------------------------------------------------------------------------- analytics


class HeatCellOut(ApiModel):
    route: str
    region: str
    period: date
    value: Decimal
    change_pct: Decimal | None


class HeatmapOut(ApiModel):
    frequency: str
    periods: list[date]
    data_origin: DataOrigin
    cells: list[HeatCellOut]


class CarrierRow(ApiModel):
    carrier_code: str
    carrier_name: str
    median_fare: Decimal
    quote_count: int
    premium_pct: Decimal | None


class CarrierAnalysis(ApiModel):
    date: date
    route: str | None
    data_origin: DataOrigin
    items: list[CarrierRow]


class ChannelRow(ApiModel):
    route: str
    direct_median: Decimal | None
    ota_median: Decimal | None
    wedge_pct: Decimal | None
    matched_fares: int


class ChannelAnalysis(ApiModel):
    date: date
    data_origin: DataOrigin
    items: list[ChannelRow]


# ----------------------------------------------------------------------------- system


class SourceHealthOut(ApiModel):
    id: str
    name: str
    kind: SourceKind
    enabled: bool
    runnable: bool
    is_synthetic: bool
    tos_reviewed: bool
    status: SourceStatus
    status_reason: str | None
    circuit_open_until: datetime | None
    consecutive_failures: int
    last_success_at: datetime | None
    rate_limit_rpm: int
    crawl_delay_s: float
    window_hours: int
    requests: int
    jobs_succeeded: int
    jobs_failed: int
    blocked: int
    rate_limited: int
    parse_errors: int
    robots_denied: int
    quotes_collected: int
    success_rate: float | None
    avg_latency_ms: float | None


class HealthBucketOut(ApiModel):
    bucket_start: datetime
    requests: int
    jobs_succeeded: int
    jobs_failed: int
    blocked: int
    parse_errors: int
    quotes_collected: int
    status_codes: dict[str, int]


class Freshness(ApiModel):
    latest_observation_at: datetime | None
    latest_observation_date: date | None
    age_seconds: float | None
    stale: bool
    latest_index_date: date | None
    latest_index_run_at: datetime | None


class SystemHealth(ApiModel):
    status: str = Field(description="ok | degraded | down")
    database: str
    freshness: Freshness
    queue: dict[str, int]
    sources: list[SourceHealthOut]


# ----------------------------------------------------------------------------- jobs


class JobOut(ApiModel):
    id: UUID
    sweep_id: UUID
    source_id: str
    route: str
    observation_date: date
    travel_date: date
    purchase_window: int
    status: JobStatus
    attempts: int
    max_attempts: int
    items_scraped: int
    errors_encountered: int
    last_error_code: str | None
    last_error_message: str | None
    started_at: datetime | None
    completed_at: datetime | None


class SweepOut(ApiModel):
    id: UUID
    slot: str
    trigger_type: SweepTrigger
    observation_date: date
    status: SweepStatus
    jobs_total: int
    created_at: datetime
    completed_at: datetime | None
    job_counts: dict[str, int]


class SweepRequest(ApiModel):
    observation_date: date | None = None
    sources: list[str] | None = None
    routes: list[str] | None = None
    windows: list[int] | None = Field(None, description="Purchase windows, e.g. [1, 7, 15, 30, 45]")


class SweepCreated(ApiModel):
    sweep_id: UUID
    slot: str
    jobs_enqueued: int
    jobs_total: int


class RequeueResult(ApiModel):
    requeued: int


# ----------------------------------------------------------------------------- backtest


class BacktestPointOut(ApiModel):
    granularity: str
    period: date
    apix_avg_fare: Decimal
    apix_index: Decimal | None
    benchmark_avg_fare: Decimal
    abs_pct_error: Decimal


class BacktestOut(ApiModel):
    id: UUID
    created_at: datetime
    period_start: date
    period_end: date
    days_covered: int
    benchmark_label: str
    benchmark_is_synthetic: bool
    apix_is_synthetic: bool
    metrics: dict[str, Any]
    verdict: str
    points: list[BacktestPointOut]


class BenchmarkOut(ApiModel):
    period_month: date
    route_code: str
    avg_fare: Decimal
    source_label: str
    source_url: str | None
    is_synthetic: bool


# ----------------------------------------------------------------------------- methodology


class Methodology(ApiModel):
    formula: str
    description: list[str]
    basket: dict[str, Any]
    fare_classes: dict[str, Any]
    purchase_windows: list[int]
    window_weights: dict[str, str]
    hedonic_adjustment: bool
    base_period: tuple[date, date] | None
    base_period_source: str | None
    cabins: list[str]
    include_connecting: bool
    quality_rules: dict[str, Any]
    external_dependencies: list[str]
    sources: list[dict[str, Any]]
