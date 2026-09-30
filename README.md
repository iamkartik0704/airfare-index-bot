# SAFAR — Real-time Airfare Price Index (APIx) for India

SIH 26056 · MoSPI (DIID). A platform that collects airline and OTA fares
ethically, keeps every raw response as evidence, cleans and de-duplicates the
quotes into a canonical dataset, computes a daily / weekly / monthly
fixed-basket Airfare Price Index with a hedonic quality adjustment, and serves
it through an API and dashboard for NSO and RBI.

```
APIx(d) = 100 · Σᵣ Wᵣ · (Pᵣ,d / Pᵣ,0) · (Q₀ / Q_d)
```

> **Data honesty.** Real airline/OTA sources ship **disabled** until their terms
> of service are reviewed (see `packages/config/reference/sources.yaml` for the
> robots.txt snapshot). The demo runs on a clearly-labelled **synthetic** market
> simulator; every API response carries `data_origin` (`live` / `simulated` /
> `mixed`) and the dashboard shows a banner. Route weights and hedonic factors
> are **indicative** until the official PSD/DGCA/NSO values are supplied.

## Architecture

The approved design is in [`docs/architecture/`](docs/architecture/ARCHITECTURE.md)
(V4). Implementation decisions and interpretations: [`docs/decisions.md`](docs/decisions.md).
Requirement map: [`docs/implementation-status.md`](docs/implementation-status.md).

```
scheduler ─▶ sweep generator ─▶ scrape_jobs (DB queue) ─▶ worker
                                                           │
   robots.txt ▸ rate limit ▸ fetch (httpx / Playwright / XHR) ▸ block detection ▸ adapter.parse
                                                           │
     evidence store (sha256) ─▶ raw_responses ─▶ raw_quotes (immutable)
                                                           │
     clean ▸ validate ▸ normalize ▸ dedup (latest wins) ▸ MAD outliers ▸ canonical per flight
                                                           │
                                               normalized_quotes
                                                           │
       index engine (pure): medians ▸ LOCF ▸ Laspeyres + hedonic ▸ D/W/M ─▶ index_values
                                                           │
                              FastAPI (router ▸ service ▸ repository) ─▶ dashboard / NSO / RBI
```

| Package | Responsibility |
|---|---|
| `packages/config` | Environment settings (`SAFAR_*`) and reference data: basket, carriers, fare classes, source policies |
| `packages/domain` | Enums, canonical Pydantic models, SQLAlchemy schema, write-side repositories, DB session |
| `packages/scraping` | Fetchers, governance (robots, blocks), rate limiting, retry, circuit breaker, engine, source adapters |
| `packages/data_pipeline` | Evidence store, cleaning, validation, normalization, deduplication, outlier detection |
| `packages/index_engine` | Pure index engine, analytics (elasticity, heatmap), back-testing, services |
| `packages/job_orchestration` | Sweep fan-out, DB-queue worker, APScheduler scheduler, `safar` CLI |
| `packages/observability` | structlog JSON logging with job context, Prometheus metrics, spans |
| `apps/api` | FastAPI: routers → services → read repositories, schemas, errors, API keys |
| `apps/dashboard` | React + Vite + Tailwind + Recharts dashboard |
| `infrastructure` | Alembic migrations, Dockerfile, Docker Compose |
| `scripts` | DGCA benchmark loader, fixture capture, live parser canary |

## Quick start (local, SQLite)

```bash
make setup                                   # uv venv + deps (Python 3.12)
cp .env.example .env
make demo                                    # migrate + 35 days of simulated data → index → back-test
make api                                     # http://localhost:8000/docs
make dashboard                               # http://localhost:5173
```

## Full stack (Docker Compose, PostgreSQL)

```bash
cp .env.example .env                          # set SAFAR_DB_PASSWORD and SAFAR_API__API_KEYS
docker compose up --build -d                  # db, migrate, api, worker, scheduler, dashboard
docker compose --profile demo run --rm demo   # optional: load simulated demo data
```

API on `:8000`, dashboard on `:3000`, Prometheus metrics on `/metrics`.

## Operating the pipeline

```bash
safar seed                                    # sync basket/sources YAML into the DB
safar sweep --route DEL-BOM --window 7        # manual sweep (idempotent per slot)
safar worker [--drain]                        # execute queued jobs
safar scheduler                               # 01:00 IST sweep, 06:30 IST index, housekeeping
safar index                                   # recompute APIx (daily/weekly/monthly)
python -m scripts.db.load_dgca_benchmark dgca.csv
safar backtest                                # compare with DGCA monthly average fares
safar requeue --failed                        # re-run dead-lettered jobs
safar replay --job <id>                       # rebuild normalized quotes from raw
safar health-check                            # structural check of each adapter's site
safar status
```

Migrations: `alembic upgrade head` (the only way the schema is created).
New migration: `alembic revision --autogenerate -m "..."`.

## Quality gates

```bash
make lint typecheck test                      # ruff, mypy --strict, pytest
SAFAR_TEST_DATABASE_URL=postgresql+psycopg://… make test-pg
```

Test layout: `tests/unit` (scraping, pipeline, index), `tests/integration`
(queue, pipeline, worker policies, migrations), `tests/api`, `tests/e2e`.
Parsers are tested offline against `tests/fixtures`; nothing in CI touches
real websites.

## Onboarding a source

1. Review the site's terms of service and robots.txt.
2. Write an adapter under `packages/scraping/sources/{airlines,otas}/<id>/`
   (reuse `common/navitaire.py` or `common/dom_cards.py` where they fit).
3. Add it to `sources/registry.py` and `packages/config/reference/sources.yaml`.
4. Capture a real fixture: `python -m scripts.scraper.capture_fixture --source <id> ...`.
5. Add fixture tests; set `enabled: true`, `tos_reviewed: true`.

Nothing downstream (pipeline, index, API, dashboard) changes.

## External inputs still required

* Official route basket and passenger weights (ps.md: "PSD given routes and weights").
* NSO hedonic methodology / fare-class quality factors.
* DGCA monthly average-fare series for the 30-day back-test.

See [`docs/implementation-status.md`](docs/implementation-status.md).

The earlier Convex prototype in `src/` is archived: [`docs/legacy-convex-prototype.md`](docs/legacy-convex-prototype.md).
