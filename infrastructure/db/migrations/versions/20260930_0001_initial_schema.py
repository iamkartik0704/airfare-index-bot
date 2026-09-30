"""initial schema

Revision ID: 0001
Revises: -
Create Date: 2026-09-30 13:04:03.289565+00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:

    op.create_table(
        "airports",
        sa.Column("code", sa.String(length=3), nullable=False),
        sa.Column("city", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.PrimaryKeyConstraint("code", name=op.f("pk_airports")),
    )
    op.create_table(
        "backtest_runs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "status",
            sa.Enum(
                "RUNNING", "SUCCESS", "FAILED", name="run_status", native_enum=False, length=32
            ),
            nullable=False,
        ),
        sa.Column("period_start", sa.Date(), nullable=False),
        sa.Column("period_end", sa.Date(), nullable=False),
        sa.Column("days_covered", sa.Integer(), nullable=False),
        sa.Column("benchmark_label", sa.String(length=256), nullable=False),
        sa.Column("benchmark_is_synthetic", sa.Boolean(), nullable=False),
        sa.Column("apix_is_synthetic", sa.Boolean(), nullable=False),
        sa.Column(
            "metrics",
            sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), "postgresql"),
            nullable=False,
        ),
        sa.Column("verdict", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "status IN ('RUNNING', 'SUCCESS', 'FAILED')", name=op.f("ck_backtest_runs_status_valid")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_backtest_runs")),
    )
    op.create_table(
        "carriers",
        sa.Column("code", sa.String(length=2), nullable=False),
        sa.Column("name", sa.String(length=64), nullable=False),
        sa.Column("group", sa.String(length=8), nullable=False),
        sa.PrimaryKeyConstraint("code", name=op.f("pk_carriers")),
    )
    op.create_table(
        "dgca_benchmarks",
        sa.Column(
            "id",
            sa.BigInteger().with_variant(sa.Integer(), "sqlite"),
            autoincrement=True,
            nullable=False,
        ),
        sa.Column("period_month", sa.Date(), nullable=False),
        sa.Column("route_code", sa.String(length=7), nullable=False),
        sa.Column("avg_fare", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("source_label", sa.String(length=256), nullable=False),
        sa.Column("source_url", sa.Text(), nullable=True),
        sa.Column("is_synthetic", sa.Boolean(), nullable=False),
        sa.Column("loaded_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_dgca_benchmarks")),
        sa.UniqueConstraint(
            "period_month", "route_code", name=op.f("uq_dgca_benchmarks_period_month_route_code")
        ),
    )
    op.create_table(
        "index_runs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "status",
            sa.Enum(
                "RUNNING", "SUCCESS", "FAILED", name="run_status", native_enum=False, length=32
            ),
            nullable=False,
        ),
        sa.Column("date_from", sa.Date(), nullable=False),
        sa.Column("date_to", sa.Date(), nullable=False),
        sa.Column("base_period_start", sa.Date(), nullable=True),
        sa.Column("base_period_end", sa.Date(), nullable=True),
        sa.Column(
            "parameters",
            sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), "postgresql"),
            nullable=False,
        ),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "status IN ('RUNNING', 'SUCCESS', 'FAILED')", name=op.f("ck_index_runs_status_valid")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_index_runs")),
    )
    op.create_table(
        "sweeps",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("slot", sa.String(length=64), nullable=False),
        sa.Column(
            "trigger_type",
            sa.Enum(
                "SCHEDULED",
                "MANUAL",
                "BACKFILL",
                name="sweep_trigger",
                native_enum=False,
                length=32,
            ),
            nullable=False,
        ),
        sa.Column("observation_date", sa.Date(), nullable=False),
        sa.Column(
            "status",
            sa.Enum(
                "RUNNING",
                "COMPLETED",
                "COMPLETED_WITH_ERRORS",
                name="sweep_status",
                native_enum=False,
                length=32,
            ),
            nullable=False,
        ),
        sa.Column("requested_by", sa.String(length=64), nullable=False),
        sa.Column(
            "parameters",
            sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), "postgresql"),
            nullable=False,
        ),
        sa.Column("jobs_total", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "status IN ('RUNNING', 'COMPLETED', 'COMPLETED_WITH_ERRORS')",
            name=op.f("ck_sweeps_status_valid"),
        ),
        sa.CheckConstraint(
            "trigger_type IN ('SCHEDULED', 'MANUAL', 'BACKFILL')",
            name=op.f("ck_sweeps_trigger_type_valid"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_sweeps")),
        sa.UniqueConstraint("slot", name=op.f("uq_sweeps_slot")),
    )
    with op.batch_alter_table("sweeps", schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f("ix_sweeps_observation_date"), ["observation_date"], unique=False
        )

    op.create_table(
        "backtest_points",
        sa.Column(
            "id",
            sa.BigInteger().with_variant(sa.Integer(), "sqlite"),
            autoincrement=True,
            nullable=False,
        ),
        sa.Column("run_id", sa.Uuid(), nullable=False),
        sa.Column("granularity", sa.String(length=8), nullable=False),
        sa.Column("period", sa.Date(), nullable=False),
        sa.Column("apix_avg_fare", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("apix_index", sa.Numeric(precision=10, scale=4), nullable=True),
        sa.Column("benchmark_avg_fare", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("abs_pct_error", sa.Numeric(precision=8, scale=4), nullable=False),
        sa.ForeignKeyConstraint(
            ["run_id"], ["backtest_runs.id"], name=op.f("fk_backtest_points_run_id_backtest_runs")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_backtest_points")),
        sa.UniqueConstraint(
            "run_id",
            "granularity",
            "period",
            name=op.f("uq_backtest_points_run_id_granularity_period"),
        ),
    )
    op.create_table(
        "index_values",
        sa.Column(
            "id",
            sa.BigInteger().with_variant(sa.Integer(), "sqlite"),
            autoincrement=True,
            nullable=False,
        ),
        sa.Column("index_run_id", sa.Uuid(), nullable=False),
        sa.Column(
            "frequency",
            sa.Enum(
                "DAILY", "WEEKLY", "MONTHLY", name="index_frequency", native_enum=False, length=32
            ),
            nullable=False,
        ),
        sa.Column(
            "scope",
            sa.Enum(
                "HEADLINE",
                "WINDOW",
                "ROUTE",
                "REGION",
                name="index_scope",
                native_enum=False,
                length=32,
            ),
            nullable=False,
        ),
        sa.Column("scope_key", sa.String(length=16), nullable=False),
        sa.Column("period_start", sa.Date(), nullable=False),
        sa.Column("period_end", sa.Date(), nullable=False),
        sa.Column("value", sa.Numeric(precision=10, scale=4), nullable=False),
        sa.Column("nominal_value", sa.Numeric(precision=10, scale=4), nullable=False),
        sa.Column("avg_fare", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("observation_count", sa.Integer(), nullable=False),
        sa.Column("coverage_pct", sa.Numeric(precision=6, scale=2), nullable=False),
        sa.Column("imputed_share", sa.Numeric(precision=6, scale=4), nullable=False),
        sa.Column("is_synthetic", sa.Boolean(), nullable=False),
        sa.CheckConstraint(
            "frequency IN ('DAILY', 'WEEKLY', 'MONTHLY')",
            name=op.f("ck_index_values_frequency_valid"),
        ),
        sa.CheckConstraint(
            "scope IN ('HEADLINE', 'WINDOW', 'ROUTE', 'REGION')",
            name=op.f("ck_index_values_scope_valid"),
        ),
        sa.ForeignKeyConstraint(
            ["index_run_id"],
            ["index_runs.id"],
            name=op.f("fk_index_values_index_run_id_index_runs"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_index_values")),
        sa.UniqueConstraint(
            "frequency",
            "scope",
            "scope_key",
            "period_start",
            name=op.f("uq_index_values_frequency_scope_scope_key_period_start"),
        ),
    )
    op.create_table(
        "routes",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("code", sa.String(length=7), nullable=False),
        sa.Column("origin_iata", sa.String(length=3), nullable=False),
        sa.Column("destination_iata", sa.String(length=3), nullable=False),
        sa.Column("distance_km", sa.Integer(), nullable=False),
        sa.Column("region", sa.String(length=16), nullable=False),
        sa.Column("dgca_weight", sa.Numeric(precision=12, scale=6), nullable=False),
        sa.Column("basket_version", sa.String(length=32), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("dgca_weight > 0", name=op.f("ck_routes_positive_weight")),
        sa.CheckConstraint(
            "origin_iata <> destination_iata", name=op.f("ck_routes_distinct_endpoints")
        ),
        sa.ForeignKeyConstraint(
            ["destination_iata"],
            ["airports.code"],
            name=op.f("fk_routes_destination_iata_airports"),
        ),
        sa.ForeignKeyConstraint(
            ["origin_iata"], ["airports.code"], name=op.f("fk_routes_origin_iata_airports")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_routes")),
        sa.UniqueConstraint("code", name=op.f("uq_routes_code")),
        sa.UniqueConstraint(
            "origin_iata", "destination_iata", name=op.f("uq_routes_origin_iata_destination_iata")
        ),
    )
    op.create_table(
        "sources",
        sa.Column("id", sa.String(length=32), nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column(
            "kind",
            sa.Enum(
                "AIRLINE", "OTA", "SIMULATED", name="source_kind", native_enum=False, length=32
            ),
            nullable=False,
        ),
        sa.Column("base_url", sa.String(length=256), nullable=False),
        sa.Column("carrier_code", sa.String(length=2), nullable=True),
        sa.Column("fetch_mode", sa.String(length=16), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("is_synthetic", sa.Boolean(), nullable=False),
        sa.Column("tos_reviewed", sa.Boolean(), nullable=False),
        sa.Column("rate_limit_rpm", sa.Integer(), nullable=False),
        sa.Column("max_concurrency", sa.SmallInteger(), nullable=False),
        sa.Column("crawl_delay_s", sa.Float(), nullable=False),
        sa.Column("channel", sa.String(length=8), nullable=False),
        sa.Column("channel_priority", sa.SmallInteger(), nullable=False),
        sa.Column(
            "status",
            sa.Enum(
                "ACTIVE",
                "DEGRADED",
                "BLOCKED",
                "DISABLED",
                name="source_status",
                native_enum=False,
                length=32,
            ),
            nullable=False,
        ),
        sa.Column("status_reason", sa.Text(), nullable=True),
        sa.Column("status_changed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("consecutive_failures", sa.Integer(), nullable=False),
        sa.Column("circuit_open_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_success_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "kind IN ('AIRLINE', 'OTA', 'SIMULATED')", name=op.f("ck_sources_kind_valid")
        ),
        sa.CheckConstraint(
            "status IN ('ACTIVE', 'DEGRADED', 'BLOCKED', 'DISABLED')",
            name=op.f("ck_sources_status_valid"),
        ),
        sa.CheckConstraint(
            "max_concurrency BETWEEN 1 AND 3", name=op.f("ck_sources_bounded_concurrency")
        ),
        sa.CheckConstraint("rate_limit_rpm > 0", name=op.f("ck_sources_positive_rate_limit")),
        sa.ForeignKeyConstraint(
            ["carrier_code"], ["carriers.code"], name=op.f("fk_sources_carrier_code_carriers")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_sources")),
    )
    op.create_table(
        "index_observations",
        sa.Column(
            "id",
            sa.BigInteger().with_variant(sa.Integer(), "sqlite"),
            autoincrement=True,
            nullable=False,
        ),
        sa.Column("index_run_id", sa.Uuid(), nullable=False),
        sa.Column("observation_date", sa.Date(), nullable=False),
        sa.Column("route_id", sa.Integer(), nullable=False),
        sa.Column("purchase_window", sa.SmallInteger(), nullable=False),
        sa.Column("median_fare", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("mean_fare", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("min_fare", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("max_fare", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("quote_count", sa.Integer(), nullable=False),
        sa.Column("source_count", sa.SmallInteger(), nullable=False),
        sa.Column("quality_factor", sa.Numeric(precision=8, scale=4), nullable=False),
        sa.Column("imputed", sa.Boolean(), nullable=False),
        sa.Column(
            "imputation_method",
            sa.Enum("NONE", "LOCF", name="imputation_method", native_enum=False, length=32),
            nullable=False,
        ),
        sa.Column("imputed_from_date", sa.Date(), nullable=True),
        sa.Column("is_synthetic", sa.Boolean(), nullable=False),
        sa.CheckConstraint(
            "imputation_method IN ('NONE', 'LOCF')",
            name=op.f("ck_index_observations_imputation_method_valid"),
        ),
        sa.ForeignKeyConstraint(
            ["index_run_id"],
            ["index_runs.id"],
            name=op.f("fk_index_observations_index_run_id_index_runs"),
        ),
        sa.ForeignKeyConstraint(
            ["route_id"], ["routes.id"], name=op.f("fk_index_observations_route_id_routes")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_index_observations")),
        sa.UniqueConstraint(
            "observation_date",
            "route_id",
            "purchase_window",
            name=op.f("uq_index_observations_observation_date_route_id_purchase_window"),
        ),
    )
    op.create_table(
        "scrape_jobs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("sweep_id", sa.Uuid(), nullable=False),
        sa.Column("source_id", sa.String(length=32), nullable=False),
        sa.Column("route_id", sa.Integer(), nullable=False),
        sa.Column("observation_date", sa.Date(), nullable=False),
        sa.Column("travel_date", sa.Date(), nullable=False),
        sa.Column("purchase_window", sa.SmallInteger(), nullable=False),
        sa.Column("idempotency_key", sa.String(length=64), nullable=False),
        sa.Column(
            "status",
            sa.Enum(
                "PENDING",
                "RUNNING",
                "RETRY",
                "SUCCESS",
                "FAILED",
                "SKIPPED",
                name="job_status",
                native_enum=False,
                length=32,
            ),
            nullable=False,
        ),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("max_attempts", sa.Integer(), nullable=False),
        sa.Column("available_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("lease_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("worker_id", sa.String(length=64), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("items_scraped", sa.Integer(), nullable=False),
        sa.Column("errors_encountered", sa.Integer(), nullable=False),
        sa.Column("last_error_code", sa.String(length=64), nullable=True),
        sa.Column("last_error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "status IN ('PENDING', 'RUNNING', 'RETRY', 'SUCCESS', 'FAILED', 'SKIPPED')",
            name=op.f("ck_scrape_jobs_status_valid"),
        ),
        sa.CheckConstraint("attempts >= 0", name=op.f("ck_scrape_jobs_non_negative_attempts")),
        sa.CheckConstraint("purchase_window >= 0", name=op.f("ck_scrape_jobs_non_negative_window")),
        sa.ForeignKeyConstraint(
            ["route_id"], ["routes.id"], name=op.f("fk_scrape_jobs_route_id_routes")
        ),
        sa.ForeignKeyConstraint(
            ["source_id"], ["sources.id"], name=op.f("fk_scrape_jobs_source_id_sources")
        ),
        sa.ForeignKeyConstraint(
            ["sweep_id"], ["sweeps.id"], name=op.f("fk_scrape_jobs_sweep_id_sweeps")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_scrape_jobs")),
        sa.UniqueConstraint("idempotency_key", name=op.f("uq_scrape_jobs_idempotency_key")),
    )
    with op.batch_alter_table("scrape_jobs", schema=None) as batch_op:
        batch_op.create_index("ix_scrape_jobs_claim", ["status", "available_at"], unique=False)
        batch_op.create_index(
            batch_op.f("ix_scrape_jobs_observation_date"), ["observation_date"], unique=False
        )
        batch_op.create_index("ix_scrape_jobs_source_status", ["source_id", "status"], unique=False)

    op.create_table(
        "source_health",
        sa.Column(
            "id",
            sa.BigInteger().with_variant(sa.Integer(), "sqlite"),
            autoincrement=True,
            nullable=False,
        ),
        sa.Column("source_id", sa.String(length=32), nullable=False),
        sa.Column("bucket_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("requests", sa.Integer(), nullable=False),
        sa.Column("jobs_succeeded", sa.Integer(), nullable=False),
        sa.Column("jobs_failed", sa.Integer(), nullable=False),
        sa.Column("blocked", sa.Integer(), nullable=False),
        sa.Column("rate_limited", sa.Integer(), nullable=False),
        sa.Column("parse_errors", sa.Integer(), nullable=False),
        sa.Column("robots_denied", sa.Integer(), nullable=False),
        sa.Column("quotes_collected", sa.Integer(), nullable=False),
        sa.Column("missing_fields", sa.Integer(), nullable=False),
        sa.Column("total_latency_ms", sa.BigInteger(), nullable=False),
        sa.Column(
            "status_codes",
            sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), "postgresql"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["source_id"], ["sources.id"], name=op.f("fk_source_health_source_id_sources")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_source_health")),
        sa.UniqueConstraint(
            "source_id", "bucket_start", name=op.f("uq_source_health_source_id_bucket_start")
        ),
    )
    op.create_table(
        "raw_responses",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("job_id", sa.Uuid(), nullable=False),
        sa.Column("source_id", sa.String(length=32), nullable=False),
        sa.Column("request_url", sa.Text(), nullable=False),
        sa.Column("request_method", sa.String(length=8), nullable=False),
        sa.Column(
            "fetch_mode",
            sa.Enum(
                "HTTP",
                "BROWSER",
                "XHR",
                "SIMULATED",
                name="fetch_mode",
                native_enum=False,
                length=32,
            ),
            nullable=False,
        ),
        sa.Column("status_code", sa.SmallInteger(), nullable=False),
        sa.Column("content_type", sa.String(length=128), nullable=True),
        sa.Column("sha256", sa.String(length=64), nullable=False),
        sa.Column("byte_size", sa.Integer(), nullable=False),
        sa.Column("storage_uri", sa.Text(), nullable=False),
        sa.Column("duration_ms", sa.Integer(), nullable=False),
        sa.Column("blocked", sa.Boolean(), nullable=False),
        sa.Column("block_reason", sa.String(length=128), nullable=True),
        sa.Column("fetched_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "fetch_mode IN ('HTTP', 'BROWSER', 'XHR', 'SIMULATED')",
            name=op.f("ck_raw_responses_fetch_mode_valid"),
        ),
        sa.ForeignKeyConstraint(
            ["job_id"], ["scrape_jobs.id"], name=op.f("fk_raw_responses_job_id_scrape_jobs")
        ),
        sa.ForeignKeyConstraint(
            ["source_id"], ["sources.id"], name=op.f("fk_raw_responses_source_id_sources")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_raw_responses")),
        sa.UniqueConstraint("job_id", "sha256", name=op.f("uq_raw_responses_job_id_sha256")),
    )
    with op.batch_alter_table("raw_responses", schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f("ix_raw_responses_fetched_at"), ["fetched_at"], unique=False
        )
        batch_op.create_index(batch_op.f("ix_raw_responses_sha256"), ["sha256"], unique=False)

    op.create_table(
        "raw_quotes",
        sa.Column(
            "id",
            sa.BigInteger().with_variant(sa.Integer(), "sqlite"),
            autoincrement=True,
            nullable=False,
        ),
        sa.Column("job_id", sa.Uuid(), nullable=False),
        sa.Column("response_id", sa.Uuid(), nullable=False),
        sa.Column("source_id", sa.String(length=32), nullable=False),
        sa.Column("route_id", sa.Integer(), nullable=False),
        sa.Column("observation_date", sa.Date(), nullable=False),
        sa.Column("travel_date", sa.Date(), nullable=False),
        sa.Column("purchase_window", sa.SmallInteger(), nullable=False),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("record_index", sa.Integer(), nullable=False),
        sa.Column(
            "raw_payload",
            sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), "postgresql"),
            nullable=False,
        ),
        sa.Column("parser_name", sa.String(length=64), nullable=False),
        sa.Column("parser_version", sa.String(length=16), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["job_id"], ["scrape_jobs.id"], name=op.f("fk_raw_quotes_job_id_scrape_jobs")
        ),
        sa.ForeignKeyConstraint(
            ["response_id"],
            ["raw_responses.id"],
            name=op.f("fk_raw_quotes_response_id_raw_responses"),
        ),
        sa.ForeignKeyConstraint(
            ["route_id"], ["routes.id"], name=op.f("fk_raw_quotes_route_id_routes")
        ),
        sa.ForeignKeyConstraint(
            ["source_id"], ["sources.id"], name=op.f("fk_raw_quotes_source_id_sources")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_raw_quotes")),
        sa.UniqueConstraint(
            "response_id",
            "record_index",
            "parser_version",
            name=op.f("uq_raw_quotes_response_id_record_index_parser_version"),
        ),
    )
    with op.batch_alter_table("raw_quotes", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_raw_quotes_created_at"), ["created_at"], unique=False)
        batch_op.create_index(batch_op.f("ix_raw_quotes_job_id"), ["job_id"], unique=False)

    op.create_table(
        "normalized_quotes",
        sa.Column(
            "id",
            sa.BigInteger().with_variant(sa.Integer(), "sqlite"),
            autoincrement=True,
            nullable=False,
        ),
        sa.Column(
            "raw_quote_id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), nullable=False
        ),
        sa.Column("job_id", sa.Uuid(), nullable=False),
        sa.Column("source_id", sa.String(length=32), nullable=False),
        sa.Column("route_id", sa.Integer(), nullable=False),
        sa.Column("carrier_code", sa.String(length=2), nullable=False),
        sa.Column("flight_number", sa.String(length=12), nullable=False),
        sa.Column("fare_class", sa.String(length=32), nullable=False),
        sa.Column("fare_family", sa.String(length=64), nullable=True),
        sa.Column(
            "cabin",
            sa.Enum(
                "ECONOMY", "PREMIUM_ECONOMY", "BUSINESS", name="cabin", native_enum=False, length=32
            ),
            nullable=False,
        ),
        sa.Column("observation_date", sa.Date(), nullable=False),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("travel_date", sa.Date(), nullable=False),
        sa.Column("departure_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("purchase_window", sa.SmallInteger(), nullable=False),
        sa.Column("advance_days", sa.SmallInteger(), nullable=False),
        sa.Column("base_fare", sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column("taxes", sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column("airport_fees", sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column("convenience_fee", sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column("total_fare", sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column(
            "availability",
            sa.Enum(
                "AVAILABLE",
                "SOLD_OUT",
                "CANCELLED",
                name="availability_status",
                native_enum=False,
                length=32,
            ),
            nullable=False,
        ),
        sa.Column("seats_left", sa.SmallInteger(), nullable=True),
        sa.Column("stops", sa.SmallInteger(), nullable=True),
        sa.Column("quality_factor", sa.Numeric(precision=8, scale=4), nullable=False),
        sa.Column("is_synthetic", sa.Boolean(), nullable=False),
        sa.Column(
            "quality_flag",
            sa.Enum(
                "VALID",
                "OUTLIER",
                "DUPLICATE",
                "INVALID",
                name="quality_flag",
                native_enum=False,
                length=32,
            ),
            nullable=False,
        ),
        sa.Column(
            "quality_reasons",
            sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), "postgresql"),
            nullable=False,
        ),
        sa.Column("dedup_key", sa.String(length=64), nullable=False),
        sa.Column("group_key", sa.String(length=64), nullable=False),
        sa.Column("is_canonical", sa.Boolean(), nullable=False),
        sa.Column("pipeline_version", sa.String(length=16), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "availability <> 'AVAILABLE' OR total_fare IS NOT NULL",
            name=op.f("ck_normalized_quotes_available_has_total"),
        ),
        sa.CheckConstraint(
            "availability IN ('AVAILABLE', 'SOLD_OUT', 'CANCELLED')",
            name=op.f("ck_normalized_quotes_availability_valid"),
        ),
        sa.CheckConstraint(
            "cabin IN ('ECONOMY', 'PREMIUM_ECONOMY', 'BUSINESS')",
            name=op.f("ck_normalized_quotes_cabin_valid"),
        ),
        sa.CheckConstraint(
            "quality_flag IN ('VALID', 'OUTLIER', 'DUPLICATE', 'INVALID')",
            name=op.f("ck_normalized_quotes_quality_flag_valid"),
        ),
        sa.CheckConstraint(
            "total_fare IS NULL OR total_fare > 0", name=op.f("ck_normalized_quotes_positive_total")
        ),
        sa.ForeignKeyConstraint(
            ["carrier_code"],
            ["carriers.code"],
            name=op.f("fk_normalized_quotes_carrier_code_carriers"),
        ),
        sa.ForeignKeyConstraint(
            ["job_id"], ["scrape_jobs.id"], name=op.f("fk_normalized_quotes_job_id_scrape_jobs")
        ),
        sa.ForeignKeyConstraint(
            ["raw_quote_id"],
            ["raw_quotes.id"],
            name=op.f("fk_normalized_quotes_raw_quote_id_raw_quotes"),
        ),
        sa.ForeignKeyConstraint(
            ["route_id"], ["routes.id"], name=op.f("fk_normalized_quotes_route_id_routes")
        ),
        sa.ForeignKeyConstraint(
            ["source_id"], ["sources.id"], name=op.f("fk_normalized_quotes_source_id_sources")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_normalized_quotes")),
        sa.UniqueConstraint("raw_quote_id", name=op.f("uq_normalized_quotes_raw_quote_id")),
    )
    with op.batch_alter_table("normalized_quotes", schema=None) as batch_op:
        batch_op.create_index(
            "ix_normalized_quotes_cell",
            ["observation_date", "route_id", "purchase_window"],
            unique=False,
        )
        batch_op.create_index("ix_normalized_quotes_dedup", ["dedup_key"], unique=False)
        batch_op.create_index("ix_normalized_quotes_group", ["group_key"], unique=False)
        batch_op.create_index(
            batch_op.f("ix_normalized_quotes_travel_date"), ["travel_date"], unique=False
        )
        batch_op.create_index(
            "uq_normalized_quotes_live_dedup",
            ["dedup_key"],
            unique=True,
            sqlite_where=sa.text("quality_flag <> 'DUPLICATE'"),
            postgresql_where=sa.text("quality_flag <> 'DUPLICATE'"),
        )


def downgrade() -> None:

    with op.batch_alter_table("normalized_quotes", schema=None) as batch_op:
        batch_op.drop_index(
            "uq_normalized_quotes_live_dedup",
            sqlite_where=sa.text("quality_flag <> 'DUPLICATE'"),
            postgresql_where=sa.text("quality_flag <> 'DUPLICATE'"),
        )
        batch_op.drop_index(batch_op.f("ix_normalized_quotes_travel_date"))
        batch_op.drop_index("ix_normalized_quotes_group")
        batch_op.drop_index("ix_normalized_quotes_dedup")
        batch_op.drop_index("ix_normalized_quotes_cell")

    op.drop_table("normalized_quotes")
    with op.batch_alter_table("raw_quotes", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_raw_quotes_job_id"))
        batch_op.drop_index(batch_op.f("ix_raw_quotes_created_at"))

    op.drop_table("raw_quotes")
    with op.batch_alter_table("raw_responses", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_raw_responses_sha256"))
        batch_op.drop_index(batch_op.f("ix_raw_responses_fetched_at"))

    op.drop_table("raw_responses")
    op.drop_table("source_health")
    with op.batch_alter_table("scrape_jobs", schema=None) as batch_op:
        batch_op.drop_index("ix_scrape_jobs_source_status")
        batch_op.drop_index(batch_op.f("ix_scrape_jobs_observation_date"))
        batch_op.drop_index("ix_scrape_jobs_claim")

    op.drop_table("scrape_jobs")
    op.drop_table("index_observations")
    op.drop_table("sources")
    op.drop_table("routes")
    op.drop_table("index_values")
    op.drop_table("backtest_points")
    with op.batch_alter_table("sweeps", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_sweeps_observation_date"))

    op.drop_table("sweeps")
    op.drop_table("index_runs")
    op.drop_table("dgca_benchmarks")
    op.drop_table("carriers")
    op.drop_table("backtest_runs")
    op.drop_table("airports")
