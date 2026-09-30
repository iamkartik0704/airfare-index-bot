"""Prometheus metrics (doc 13 "Metrics").

Names follow doc 13 with a ``safar_`` namespace. The API exposes them on
``/metrics``; the worker exposes them on ``SAFAR_WORKER_METRICS_PORT``.
Rates such as ``scrape_success_rate`` are derived in PromQL from the counters
(e.g. ``sum(rate(safar_scrape_jobs_total{outcome="success"}[1h])) by (source)``).
"""

from __future__ import annotations

from prometheus_client import CollectorRegistry, Counter, Gauge, Histogram

REGISTRY = CollectorRegistry(auto_describe=True)

SCRAPE_REQUESTS = Counter(
    "safar_http_requests_total",
    "Requests sent to sources, by HTTP status (doc 13 http_status_codes).",
    ["source", "status"],
    registry=REGISTRY,
)
SCRAPE_LATENCY = Histogram(
    "safar_scrape_request_seconds",
    "Latency of a single source request.",
    ["source", "mode"],
    buckets=(0.1, 0.25, 0.5, 1, 2, 5, 10, 20, 45, 90),
    registry=REGISTRY,
)
SCRAPE_JOBS = Counter(
    "safar_scrape_jobs_total",
    "Scrape jobs finished, by outcome (success, retry, failed, skipped).",
    ["source", "outcome"],
    registry=REGISTRY,
)
SCRAPE_BLOCKS = Counter(
    "safar_block_events_total",
    "Challenge / CAPTCHA / 403 responses detected (never bypassed).",
    ["source"],
    registry=REGISTRY,
)
ROBOTS_DENIED = Counter(
    "safar_robots_denied_total",
    "Requests not sent because robots.txt disallowed them.",
    ["source"],
    registry=REGISTRY,
)
PARSER_FAILURES = Counter(
    "safar_parser_failures_total",
    "Responses the adapter could not parse (doc 13).",
    ["source"],
    registry=REGISTRY,
)
QUOTES_COLLECTED = Counter(
    "safar_quotes_collected_total", "Raw quotes extracted.", ["source"], registry=REGISTRY
)
MISSING_FARE_FIELDS = Counter(
    "safar_missing_fare_count_total",
    "Normalized quotes missing an optional fare component (doc 13 missing_fare_count).",
    ["source", "field"],
    registry=REGISTRY,
)
PIPELINE_QUOTES = Counter(
    "safar_pipeline_quotes_total",
    "Quotes leaving the pipeline, by quality flag.",
    ["flag"],
    registry=REGISTRY,
)
SOURCE_UP = Gauge(
    "safar_source_up",
    "1 if the source circuit is closed and not blocked.",
    ["source"],
    registry=REGISTRY,
)
DATA_FRESHNESS = Gauge(
    "safar_data_freshness_seconds",
    "Seconds since the newest canonical quote was observed (doc 13).",
    registry=REGISTRY,
)
ROUTE_COVERAGE = Gauge(
    "safar_route_coverage_ratio",
    "Share of basket route×window cells with observations for the latest index date.",
    registry=REGISTRY,
)
INDEX_RUNS = Counter(
    "safar_index_runs_total", "Index computations by status.", ["status"], registry=REGISTRY
)
INDEX_VALUE = Gauge("safar_index_value", "Latest headline daily APIx value.", registry=REGISTRY)
QUEUE_DEPTH = Gauge("safar_queue_depth", "Scrape jobs by status.", ["status"], registry=REGISTRY)
