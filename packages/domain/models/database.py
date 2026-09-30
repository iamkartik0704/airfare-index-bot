"""SQLAlchemy schema (doc 08 Database Architecture).

The schema is created and evolved **only** through Alembic migrations in
``infrastructure/db/migrations``. Types are chosen to run on PostgreSQL in
production and SQLite in unit tests:

* JSON columns become ``JSONB`` on PostgreSQL (raw payloads, run parameters).
* Money is ``NUMERIC(12,2)`` rupees; nothing monetary is stored as float.
* Timestamps are timezone-aware UTC (``UTCDateTime`` re-attaches UTC on SQLite).

Lineage (doc 06 "Job IDs … trace any anomaly back to the exact response"):

    index_values ─┐
    index_observations ─→ normalized_quotes ─→ raw_quotes ─→ raw_responses
                                    │                 │            │
                                    └────────→ scrape_jobs ←───────┘ ─→ sweeps
                                                     └─→ sources
"""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime
from decimal import Decimal
from enum import StrEnum
from typing import Any

from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    Integer,
    MetaData,
    Numeric,
    SmallInteger,
    String,
    Text,
    TypeDecorator,
    UniqueConstraint,
    Uuid,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.engine import Dialect
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from packages.domain.enums import (
    AvailabilityStatus,
    Cabin,
    FetchMode,
    ImputationMethod,
    IndexFrequency,
    IndexScope,
    JobStatus,
    QualityFlag,
    RunStatus,
    SourceKind,
    SourceStatus,
    SweepStatus,
    SweepTrigger,
)

NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_N_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}

JSONType = JSON().with_variant(JSONB(), "postgresql")
BigIntPK = BigInteger().with_variant(Integer(), "sqlite")
Money = Numeric(12, 2)


class UTCDateTime(TypeDecorator[datetime]):
    """Timezone-aware UTC timestamps on every backend."""

    impl = DateTime(timezone=True)
    cache_ok = True

    def process_bind_param(self, value: datetime | None, dialect: Dialect) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            raise ValueError("naive datetime passed to a UTC column")
        return value.astimezone(UTC)

    def process_result_value(self, value: datetime | None, dialect: Dialect) -> datetime | None:
        if value is None:
            return None
        return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


def utcnow() -> datetime:
    return datetime.now(UTC)


def _enum(enum_cls: type[Any], name: str) -> Enum:
    # Stored as VARCHAR; the allowed values are enforced by an explicit, named
    # CHECK constraint (``_enum_check``) so adding a member is a plain migration.
    return Enum(
        enum_cls,
        name=name,
        native_enum=False,
        create_constraint=False,
        length=32,
        values_callable=lambda members: [m.value for m in members],
        validate_strings=True,
    )


def _enum_check(column: str, enum_cls: type[StrEnum]) -> CheckConstraint:
    values = ", ".join(f"'{member.value}'" for member in enum_cls)
    return CheckConstraint(f"{column} IN ({values})", name=f"{column}_valid")


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING_CONVENTION)


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        UTCDateTime(), default=utcnow, onupdate=utcnow, nullable=False
    )


# --------------------------------------------------------------------------- reference data


class Airport(Base):
    __tablename__ = "airports"

    code: Mapped[str] = mapped_column(String(3), primary_key=True)
    city: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str] = mapped_column(String(128), nullable=False)


class Carrier(Base):
    __tablename__ = "carriers"

    code: Mapped[str] = mapped_column(String(2), primary_key=True)
    name: Mapped[str] = mapped_column(String(64), nullable=False)
    group: Mapped[str] = mapped_column(String(8), nullable=False)


class Route(TimestampMixin, Base):
    __tablename__ = "routes"
    __table_args__ = (
        UniqueConstraint("origin_iata", "destination_iata"),
        CheckConstraint("origin_iata <> destination_iata", name="distinct_endpoints"),
        CheckConstraint("dgca_weight > 0", name="positive_weight"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(7), unique=True, nullable=False)
    origin_iata: Mapped[str] = mapped_column(ForeignKey("airports.code"), nullable=False)
    destination_iata: Mapped[str] = mapped_column(ForeignKey("airports.code"), nullable=False)
    distance_km: Mapped[int] = mapped_column(Integer, nullable=False)
    region: Mapped[str] = mapped_column(String(16), nullable=False)
    dgca_weight: Mapped[Decimal] = mapped_column(Numeric(12, 6), nullable=False)
    basket_version: Mapped[str] = mapped_column(String(32), nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class Source(TimestampMixin, Base):
    __tablename__ = "sources"
    __table_args__ = (
        CheckConstraint("rate_limit_rpm > 0", name="positive_rate_limit"),
        CheckConstraint("max_concurrency BETWEEN 1 AND 3", name="bounded_concurrency"),
        _enum_check("kind", SourceKind),
        _enum_check("status", SourceStatus),
    )

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    kind: Mapped[SourceKind] = mapped_column(_enum(SourceKind, "source_kind"), nullable=False)
    base_url: Mapped[str] = mapped_column(String(256), nullable=False)
    carrier_code: Mapped[str | None] = mapped_column(ForeignKey("carriers.code"))
    fetch_mode: Mapped[str] = mapped_column(String(16), nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_synthetic: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    tos_reviewed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    rate_limit_rpm: Mapped[int] = mapped_column(Integer, nullable=False)
    max_concurrency: Mapped[int] = mapped_column(SmallInteger, default=1, nullable=False)
    crawl_delay_s: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    channel: Mapped[str] = mapped_column(String(8), nullable=False)
    channel_priority: Mapped[int] = mapped_column(SmallInteger, default=10, nullable=False)
    status: Mapped[SourceStatus] = mapped_column(
        _enum(SourceStatus, "source_status"), default=SourceStatus.ACTIVE, nullable=False
    )
    status_reason: Mapped[str | None] = mapped_column(Text)
    status_changed_at: Mapped[datetime | None] = mapped_column(UTCDateTime())
    # Circuit breaker state is persisted so it survives worker restarts (doc 04).
    consecutive_failures: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    circuit_open_until: Mapped[datetime | None] = mapped_column(UTCDateTime())
    last_success_at: Mapped[datetime | None] = mapped_column(UTCDateTime())


# --------------------------------------------------------------------------- orchestration


class Sweep(Base):
    __tablename__ = "sweeps"
    __table_args__ = (
        _enum_check("trigger_type", SweepTrigger),
        _enum_check("status", SweepStatus),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    # Idempotency: one sweep per scheduled slot ("2026-09-30T01:00+05:30").
    slot: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    trigger_type: Mapped[SweepTrigger] = mapped_column(
        _enum(SweepTrigger, "sweep_trigger"), nullable=False
    )
    observation_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    status: Mapped[SweepStatus] = mapped_column(
        _enum(SweepStatus, "sweep_status"), default=SweepStatus.RUNNING, nullable=False
    )
    requested_by: Mapped[str] = mapped_column(String(64), default="scheduler", nullable=False)
    parameters: Mapped[dict[str, Any]] = mapped_column(JSONType, default=dict, nullable=False)
    jobs_total: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utcnow, nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(UTCDateTime())

    jobs: Mapped[list[ScrapeJob]] = relationship(back_populates="sweep")


class ScrapeJob(TimestampMixin, Base):
    """One source × route × travel date × purchase window task (doc 10)."""

    __tablename__ = "scrape_jobs"
    __table_args__ = (
        Index("ix_scrape_jobs_claim", "status", "available_at"),
        Index("ix_scrape_jobs_source_status", "source_id", "status"),
        CheckConstraint("attempts >= 0", name="non_negative_attempts"),
        CheckConstraint("purchase_window >= 0", name="non_negative_window"),
        _enum_check("status", JobStatus),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    sweep_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("sweeps.id"), nullable=False)
    source_id: Mapped[str] = mapped_column(ForeignKey("sources.id"), nullable=False)
    route_id: Mapped[int] = mapped_column(ForeignKey("routes.id"), nullable=False)
    observation_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    travel_date: Mapped[date] = mapped_column(Date, nullable=False)
    purchase_window: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    #: sha256(slot|source|route|travel_date|window) — a logical task is enqueued once.
    idempotency_key: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    status: Mapped[JobStatus] = mapped_column(
        _enum(JobStatus, "job_status"), default=JobStatus.PENDING, nullable=False
    )
    attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    max_attempts: Mapped[int] = mapped_column(Integer, default=3, nullable=False)
    available_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utcnow, nullable=False)
    lease_expires_at: Mapped[datetime | None] = mapped_column(UTCDateTime())
    worker_id: Mapped[str | None] = mapped_column(String(64))
    started_at: Mapped[datetime | None] = mapped_column(UTCDateTime())
    completed_at: Mapped[datetime | None] = mapped_column(UTCDateTime())
    items_scraped: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    errors_encountered: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_error_code: Mapped[str | None] = mapped_column(String(64))
    last_error_message: Mapped[str | None] = mapped_column(Text)

    sweep: Mapped[Sweep] = relationship(back_populates="jobs")
    source: Mapped[Source] = relationship()
    route: Mapped[Route] = relationship()


# --------------------------------------------------------------------------- raw store


class RawResponse(Base):
    """Evidence: one fetched response. Body lives in the content-addressed store."""

    __tablename__ = "raw_responses"
    __table_args__ = (UniqueConstraint("job_id", "sha256"), _enum_check("fetch_mode", FetchMode))

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    job_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("scrape_jobs.id"), nullable=False)
    source_id: Mapped[str] = mapped_column(ForeignKey("sources.id"), nullable=False)
    request_url: Mapped[str] = mapped_column(Text, nullable=False)
    request_method: Mapped[str] = mapped_column(String(8), default="GET", nullable=False)
    fetch_mode: Mapped[FetchMode] = mapped_column(_enum(FetchMode, "fetch_mode"), nullable=False)
    status_code: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    content_type: Mapped[str | None] = mapped_column(String(128))
    sha256: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    byte_size: Mapped[int] = mapped_column(Integer, nullable=False)
    storage_uri: Mapped[str] = mapped_column(Text, nullable=False)
    duration_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    blocked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    block_reason: Mapped[str | None] = mapped_column(String(128))
    fetched_at: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False, index=True)


class RawQuote(Base):
    """Immutable audit log of every parsed fare, unparsed field text in ``raw_payload``."""

    __tablename__ = "raw_quotes"
    __table_args__ = (UniqueConstraint("response_id", "record_index", "parser_version"),)

    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True, autoincrement=True)
    job_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("scrape_jobs.id"), nullable=False, index=True
    )
    response_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("raw_responses.id"), nullable=False)
    source_id: Mapped[str] = mapped_column(ForeignKey("sources.id"), nullable=False)
    route_id: Mapped[int] = mapped_column(ForeignKey("routes.id"), nullable=False)
    observation_date: Mapped[date] = mapped_column(Date, nullable=False)
    travel_date: Mapped[date] = mapped_column(Date, nullable=False)
    purchase_window: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    observed_at: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False)
    record_index: Mapped[int] = mapped_column(Integer, nullable=False)
    raw_payload: Mapped[dict[str, Any]] = mapped_column(JSONType, nullable=False)
    parser_name: Mapped[str] = mapped_column(String(64), nullable=False)
    parser_version: Mapped[str] = mapped_column(String(16), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        UTCDateTime(), default=utcnow, nullable=False, index=True
    )

    response: Mapped[RawResponse] = relationship()


# --------------------------------------------------------------------------- canonical data


class NormalizedQuote(TimestampMixin, Base):
    """Canonical airfare observation (doc 06 ``AirfareQuote``, doc 08 ``normalized_quotes``)."""

    __tablename__ = "normalized_quotes"
    __table_args__ = (
        Index("ix_normalized_quotes_cell", "observation_date", "route_id", "purchase_window"),
        Index("ix_normalized_quotes_group", "group_key"),
        Index("ix_normalized_quotes_dedup", "dedup_key"),
        # At most one live observation per within-source dedup key (doc 07 "latest wins").
        Index(
            "uq_normalized_quotes_live_dedup",
            "dedup_key",
            unique=True,
            sqlite_where=text("quality_flag <> 'DUPLICATE'"),
            postgresql_where=text("quality_flag <> 'DUPLICATE'"),
        ),
        CheckConstraint(
            "availability <> 'AVAILABLE' OR total_fare IS NOT NULL", name="available_has_total"
        ),
        CheckConstraint("total_fare IS NULL OR total_fare > 0", name="positive_total"),
        _enum_check("cabin", Cabin),
        _enum_check("availability", AvailabilityStatus),
        _enum_check("quality_flag", QualityFlag),
    )

    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True, autoincrement=True)
    raw_quote_id: Mapped[int] = mapped_column(
        ForeignKey("raw_quotes.id"), unique=True, nullable=False
    )
    job_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("scrape_jobs.id"), nullable=False)
    source_id: Mapped[str] = mapped_column(ForeignKey("sources.id"), nullable=False)
    route_id: Mapped[int] = mapped_column(ForeignKey("routes.id"), nullable=False)
    carrier_code: Mapped[str] = mapped_column(ForeignKey("carriers.code"), nullable=False)
    flight_number: Mapped[str] = mapped_column(String(12), nullable=False)
    fare_class: Mapped[str] = mapped_column(String(32), nullable=False)
    fare_family: Mapped[str | None] = mapped_column(String(64))
    cabin: Mapped[Cabin] = mapped_column(_enum(Cabin, "cabin"), nullable=False)
    observation_date: Mapped[date] = mapped_column(Date, nullable=False)
    observed_at: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False)
    travel_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    departure_at: Mapped[datetime | None] = mapped_column(UTCDateTime())
    purchase_window: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    advance_days: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    base_fare: Mapped[Decimal | None] = mapped_column(Money)
    taxes: Mapped[Decimal | None] = mapped_column(Money)
    airport_fees: Mapped[Decimal | None] = mapped_column(Money)
    convenience_fee: Mapped[Decimal | None] = mapped_column(Money)
    total_fare: Mapped[Decimal | None] = mapped_column(Money)
    currency: Mapped[str] = mapped_column(String(3), default="INR", nullable=False)
    availability: Mapped[AvailabilityStatus] = mapped_column(
        _enum(AvailabilityStatus, "availability_status"), nullable=False
    )
    seats_left: Mapped[int | None] = mapped_column(SmallInteger)
    stops: Mapped[int | None] = mapped_column(SmallInteger)
    quality_factor: Mapped[Decimal] = mapped_column(Numeric(8, 4), nullable=False)
    is_synthetic: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    quality_flag: Mapped[QualityFlag] = mapped_column(
        _enum(QualityFlag, "quality_flag"), default=QualityFlag.VALID, nullable=False
    )
    quality_reasons: Mapped[list[str]] = mapped_column(JSONType, default=list, nullable=False)
    #: Within-source identity: source|carrier|flight|fare class|travel date|observation date.
    dedup_key: Mapped[str] = mapped_column(String(64), nullable=False)
    #: Cross-channel identity: carrier|flight|fare class|travel date|observation date.
    group_key: Mapped[str] = mapped_column(String(64), nullable=False)
    #: The one representative of ``group_key`` the index uses (airline direct preferred).
    is_canonical: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    pipeline_version: Mapped[str] = mapped_column(String(16), nullable=False)

    raw_quote: Mapped[RawQuote] = relationship()
    route: Mapped[Route] = relationship()
    source: Mapped[Source] = relationship()


# --------------------------------------------------------------------------- index store


class IndexRun(Base):
    __tablename__ = "index_runs"
    __table_args__ = (_enum_check("status", RunStatus),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    status: Mapped[RunStatus] = mapped_column(_enum(RunStatus, "run_status"), nullable=False)
    date_from: Mapped[date] = mapped_column(Date, nullable=False)
    date_to: Mapped[date] = mapped_column(Date, nullable=False)
    base_period_start: Mapped[date | None] = mapped_column(Date)
    base_period_end: Mapped[date | None] = mapped_column(Date)
    #: Snapshot of weights, window weights, hedonic factors and basket version used.
    parameters: Mapped[dict[str, Any]] = mapped_column(JSONType, default=dict, nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text)
    started_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utcnow, nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(UTCDateTime())


class IndexObservationRow(Base):
    """Elementary aggregate per (date, route, window) — doc 08 ``index_observations``."""

    __tablename__ = "index_observations"
    __table_args__ = (
        UniqueConstraint("observation_date", "route_id", "purchase_window"),
        _enum_check("imputation_method", ImputationMethod),
    )

    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True, autoincrement=True)
    index_run_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("index_runs.id"), nullable=False)
    observation_date: Mapped[date] = mapped_column(Date, nullable=False)
    route_id: Mapped[int] = mapped_column(ForeignKey("routes.id"), nullable=False)
    purchase_window: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    median_fare: Mapped[Decimal] = mapped_column(Money, nullable=False)
    mean_fare: Mapped[Decimal] = mapped_column(Money, nullable=False)
    min_fare: Mapped[Decimal] = mapped_column(Money, nullable=False)
    max_fare: Mapped[Decimal] = mapped_column(Money, nullable=False)
    quote_count: Mapped[int] = mapped_column(Integer, nullable=False)
    source_count: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    quality_factor: Mapped[Decimal] = mapped_column(Numeric(8, 4), nullable=False)
    imputed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    imputation_method: Mapped[ImputationMethod] = mapped_column(
        _enum(ImputationMethod, "imputation_method"), nullable=False
    )
    imputed_from_date: Mapped[date | None] = mapped_column(Date)
    is_synthetic: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    route: Mapped[Route] = relationship()


class IndexValueRow(Base):
    __tablename__ = "index_values"
    __table_args__ = (
        UniqueConstraint("frequency", "scope", "scope_key", "period_start"),
        _enum_check("frequency", IndexFrequency),
        _enum_check("scope", IndexScope),
    )

    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True, autoincrement=True)
    index_run_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("index_runs.id"), nullable=False)
    frequency: Mapped[IndexFrequency] = mapped_column(
        _enum(IndexFrequency, "index_frequency"), nullable=False
    )
    scope: Mapped[IndexScope] = mapped_column(_enum(IndexScope, "index_scope"), nullable=False)
    scope_key: Mapped[str] = mapped_column(String(16), default="", nullable=False)
    period_start: Mapped[date] = mapped_column(Date, nullable=False)
    period_end: Mapped[date] = mapped_column(Date, nullable=False)
    value: Mapped[Decimal] = mapped_column(Numeric(10, 4), nullable=False)
    nominal_value: Mapped[Decimal] = mapped_column(Numeric(10, 4), nullable=False)
    avg_fare: Mapped[Decimal] = mapped_column(Money, nullable=False)
    observation_count: Mapped[int] = mapped_column(Integer, nullable=False)
    coverage_pct: Mapped[Decimal] = mapped_column(Numeric(6, 2), nullable=False)
    imputed_share: Mapped[Decimal] = mapped_column(Numeric(6, 4), nullable=False)
    is_synthetic: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)


# --------------------------------------------------------------------------- health & validation


class SourceHealth(Base):
    """Hourly per-source health counters (doc 13 metrics, persisted for the console)."""

    __tablename__ = "source_health"
    __table_args__ = (UniqueConstraint("source_id", "bucket_start"),)

    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True, autoincrement=True)
    source_id: Mapped[str] = mapped_column(ForeignKey("sources.id"), nullable=False)
    bucket_start: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False)
    requests: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    jobs_succeeded: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    jobs_failed: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    blocked: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    rate_limited: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    parse_errors: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    robots_denied: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    quotes_collected: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    missing_fields: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_latency_ms: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    status_codes: Mapped[dict[str, int]] = mapped_column(JSONType, default=dict, nullable=False)


class DgcaBenchmark(Base):
    """External DGCA monthly average fare (ps.md backtest). Loaded from CSV."""

    __tablename__ = "dgca_benchmarks"
    __table_args__ = (UniqueConstraint("period_month", "route_code"),)

    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True, autoincrement=True)
    period_month: Mapped[date] = mapped_column(Date, nullable=False)
    #: A basket route code ("DEL-BOM") or "ALL" for an all-India figure.
    route_code: Mapped[str] = mapped_column(String(7), nullable=False, default="ALL")
    avg_fare: Mapped[Decimal] = mapped_column(Money, nullable=False)
    source_label: Mapped[str] = mapped_column(String(256), nullable=False)
    source_url: Mapped[str | None] = mapped_column(Text)
    is_synthetic: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    loaded_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utcnow, nullable=False)


class BacktestRun(Base):
    __tablename__ = "backtest_runs"
    __table_args__ = (_enum_check("status", RunStatus),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    status: Mapped[RunStatus] = mapped_column(_enum(RunStatus, "run_status"), nullable=False)
    period_start: Mapped[date] = mapped_column(Date, nullable=False)
    period_end: Mapped[date] = mapped_column(Date, nullable=False)
    days_covered: Mapped[int] = mapped_column(Integer, nullable=False)
    benchmark_label: Mapped[str] = mapped_column(String(256), nullable=False)
    benchmark_is_synthetic: Mapped[bool] = mapped_column(Boolean, nullable=False)
    apix_is_synthetic: Mapped[bool] = mapped_column(Boolean, nullable=False)
    metrics: Mapped[dict[str, Any]] = mapped_column(JSONType, default=dict, nullable=False)
    verdict: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utcnow, nullable=False)

    points: Mapped[list[BacktestPoint]] = relationship(
        back_populates="run", cascade="all, delete-orphan", order_by="BacktestPoint.period"
    )


class BacktestPoint(Base):
    __tablename__ = "backtest_points"
    __table_args__ = (UniqueConstraint("run_id", "granularity", "period"),)

    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True, autoincrement=True)
    run_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("backtest_runs.id"), nullable=False)
    granularity: Mapped[str] = mapped_column(String(8), nullable=False)  # DAY | MONTH
    period: Mapped[date] = mapped_column(Date, nullable=False)
    apix_avg_fare: Mapped[Decimal] = mapped_column(Money, nullable=False)
    apix_index: Mapped[Decimal | None] = mapped_column(Numeric(10, 4))
    benchmark_avg_fare: Mapped[Decimal] = mapped_column(Money, nullable=False)
    abs_pct_error: Mapped[Decimal] = mapped_column(Numeric(8, 4), nullable=False)

    run: Mapped[BacktestRun] = relationship(back_populates="points")
