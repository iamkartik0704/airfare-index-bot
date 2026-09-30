# Implementation Status — Requirement-to-Code Map

Source of truth: `ps.md` → `docs/architecture/*.md` (V4) → this map.
Status legend: **DONE** · **PARTIAL** · **MISSING** · **NEEDS_REFACTOR**

The "Initial" column records what was found when implementation started
(2026-09-30); "Target" is the planned end state; verified status is tracked milestone-by-milestone in `docs/progress.md`.

| # | Requirement (ps.md / docs) | Subsystem (doc) | Package / module | Initial | Target (planned → verified in progress.md) | Tests |
|---|---|---|---|---|---|---|
| R1 | Multi-source scraping engine (airline + OTA) | Scraping engine (04) | `packages/scraping/core/*`, `packages/scraping/engine.py` | PARTIAL (bare fetchers) | DONE | `tests/unit/scraping/` |
| R2 | JS-rendered pages, XHR/JSON capture | Scraping engine (04, 19) | `packages/scraping/core/fetchers/browser.py` | PARTIAL | DONE (Playwright, XHR capture, resource blocking) | fetcher unit tests (browser mocked) |
| R3 | Source adapter contract (`metadata`, `build_requests`, `parse`, `health_check`) | Source adapters (05) | `packages/scraping/sources/base.py`, `registry.py` | NEEDS_REFACTOR (copy-pasted fake stubs) | DONE | adapter fixture tests |
| R4 | First airline: IndiGo (Stage 3) | Adapters (05, 17) | `packages/scraping/sources/airlines/indigo/` | NEEDS_REFACTOR | DONE (fixture-validated) | `tests/unit/scraping/test_indigo_adapter.py` |
| R5 | Additional sources: Air India, MMT, Yatra, … (Stage 8) | Adapters (05, 17) | `sources/airlines/*`, `sources/otas/*` | NEEDS_REFACTOR | see `docs/progress.md` | per-adapter fixture tests |
| R6 | CAPTCHA/anti-bot: detect, back off, never bypass | Governance (15, 19) | `packages/scraping/core/governance/` | PARTIAL (proxy heuristics) | DONE | block-detection tests |
| R7 | robots.txt + Crawl-delay | Governance (15) | `core/governance/robots.py` | MISSING | DONE | robots tests |
| R8 | Per-domain token-bucket rate limit, concurrency cap | Governance (10, 15) | `core/rate_limit/` | MISSING | DONE | rate-limit tests |
| R9 | Retries with exponential backoff, circuit breaker (5 failures → DEGRADED) | Scraping + orchestration (04, 10) | `core/resilience/` | MISSING | DONE | resilience tests |
| R10 | Session management | Scraping (04) | `core/session/` | PARTIAL | DONE | session tests |
| R11 | Proxy abstraction (configurable, not evasion) | Scraping (04, 15) | `core/proxy/` | PARTIAL | DONE (config-driven, off by default) | proxy tests |
| R12 | Canonical domain model (`AirfareQuote`, `ScrapeJob`, `IndexObservation`, …) | Domain (06) | `packages/domain/models/` | NEEDS_REFACTOR (two conflicting ORM copies) | DONE | domain tests |
| R13 | Raw data preserved & replayable (evidence) | Pipeline (07), DB (08), V3 review | `packages/domain/models/database.py` (`raw_responses`, `raw_quotes`), `packages/data_pipeline/evidence.py` | MISSING | DONE | replay tests |
| R14 | Validation + currency parsing ("₹ 5,400" → 5400.00) | Pipeline (07) | `packages/data_pipeline/validation/`, `cleaning/` | PARTIAL (floats, returns 0.0 on failure) | DONE | pipeline unit tests |
| R15 | Normalization (carrier codes, fare classes, windows) | Pipeline (07) | `packages/data_pipeline/normalization/` | PARTIAL | DONE | |
| R16 | Fare breakdown: base, taxes, UDF/airport fees, convenience fee, total | Domain + pipeline (06, 07) | `normalized_quotes` columns | PARTIAL (no UDF) | DONE | |
| R17 | Sold-out / cancelled handling | Domain (06), pipeline | `AvailabilityStatus` | MISSING | DONE | |
| R18 | Deduplication (within-source + cross-channel) | Pipeline (07) | `packages/data_pipeline/deduplication/` | PARTIAL (fuzzy string match on dicts) | DONE | |
| R19 | Outlier detection (MAD) + quarantine | Pipeline (07) | `packages/data_pipeline/validation/outliers.py` | PARTIAL (buggy: NameError path) | DONE | |
| R20 | Relational DB with migrations, FKs, constraints, indexes | DB (08) | `packages/domain/models/database.py`, `infrastructure/db/migrations/` | NEEDS_REFACTOR (`create_all` at API import) | DONE (Alembic) | DB/repository tests |
| R21 | Idempotent jobs & loads | Orchestration (10) | `scrape_jobs.idempotency_key`, upserts | MISSING | DONE | idempotency tests |
| R22 | Sweep fan-out: route × source × window (T+1/7/15/30/45) | Orchestration (10) | `packages/job_orchestration/sweep.py` | MISSING (commented-out loop) | DONE | |
| R23 | Scheduler (01:00 IST), retries, timeouts, per-source limits, DLQ, manual reruns, restart recovery | Orchestration (10, 16) | `packages/job_orchestration/{queue,worker,scheduler}.py` | MISSING | DONE (DB queue + APScheduler) | queue/worker tests |
| R24 | Index engine: Laspeyres, medians, LOCF, DGCA weights, base period | Index engine (09) | `packages/index_engine/` | PARTIAL (toy function) | DONE | deterministic index tests |
| R25 | Daily / weekly / monthly indices, window sub-indices | Index engine (09) | `index_engine/aggregation/` | MISSING | DONE | |
| R26 | Hedonic quality adjustment `Q(0)/Q(d)` | Index engine (09) | `index_engine/methodology/hedonic.py` | MISSING | DONE (factors configurable; indicative defaults) | |
| R27 | Route analytics, carrier analysis, lead-time elasticity, sector heatmap | Index engine + API (09, 11, 12) | `packages/index_engine/analytics.py`, API services | MISSING | DONE | |
| R28 | 30-day backtest vs DGCA monthly average fare | Index engine / testing (01, 14) | `packages/index_engine/backtesting.py`, `scripts/backtest.py` | PARTIAL (random mock data) | DONE (needs real DGCA CSV — see external deps) | |
| R29 | Index lineage / auditability | 06, 07 | lineage service + endpoint | MISSING | DONE | e2e test |
| R30 | REST API (router → service → repository), schemas, errors, pagination | API (11) | `apps/api/` | NEEDS_REFACTOR (logic in routers, hard-coded responses) | DONE | `tests/api/` |
| R31 | Protected quotes download for NSO analysts | API (11) | API-key dependency | MISSING | DONE | |
| R32 | Source health & data freshness | Observability (13), API (11) | `source_health`, `/api/v1/system/health` | MISSING | DONE | |
| R33 | Structured logging (`job_id`, `source`, `event`) | Observability (13) | `packages/observability/logging/` | PARTIAL | DONE (structlog + contextvars) | |
| R34 | Prometheus metrics | Observability (13) | `packages/observability/metrics/` | PARTIAL | DONE + `/metrics` | |
| R35 | Dashboard: headline vs DGCA, heatmap, elasticity, system console | Dashboard (12) | `apps/dashboard/` | PARTIAL (3 toy components; rich UI lives on legacy Convex app) | see progress | build check |
| R36 | Centralised config / env, no secrets in code | 15 | `packages/config/` | MISSING (hard-coded URLs, creds in compose) | DONE | settings tests |
| R37 | Docker Compose (Postgres, API, worker, scheduler, dashboard) | Deployment (16) | `infrastructure/docker/` | NEEDS_REFACTOR | DONE | startup check |
| R38 | Offline parser fixtures, unit / contract / integration / e2e tests | Testing (14) | `tests/` | PARTIAL | DONE | — |
| R39 | Nightly live regression canary (5 URLs/source) | Testing (14) | `scripts/scraper/canary.py` | MISSING | DONE (manual/cron; not in CI) | |
| R40 | Documentation | all | `docs/`, `README` | PARTIAL | see progress | — |

## External dependencies (cannot be completed from this repository alone)

| Dependency | Needed for | Where it plugs in |
|---|---|---|
| Official route basket & weights ("PSD given routes and weights", ps.md §Expected Solution c) | Index weights `wᵣ` | `packages/config/reference/basket.yaml` (current values are *indicative* placeholders) |
| DGCA monthly average-fare series | 30-day backtest (ps.md) | `scripts/db/load_dgca_benchmark.py <csv>` → `dgca_benchmarks` |
| NSO hedonic quality factors / fare-class mapping | `Q(d)` adjustment | `packages/config/reference/fare_classes.yaml` |
| ToS / robots review and real payload captures per source | Live scraping | `scripts/scraper/capture_fixture.py`, `packages/config/reference/sources.yaml` |
