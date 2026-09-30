# Implementation Decisions

Decisions taken while implementing the V4 architecture (`docs/architecture/`).
Each entry records the doc(s) involved, the choice, and why. Architecture docs
are not edited to match code; where the docs were ambiguous or contradictory,
the interpretation is recorded here.

---

## D1 — Orchestration: Postgres-backed job queue + APScheduler (no Celery/Redis)

* **Docs:** 02 (“a relational table `scrape_jobs` managed by APScheduler or a
  lightweight Celery”), 10 (Celery + Redis), 16 (prototype: “APScheduler or
  background asyncio tasks instead of Celery/Redis”), 00 (“Celery/Redis or
  APScheduler”).
* **Choice:** `scrape_jobs` *is* the queue. Workers claim jobs with an atomic
  compare-and-set `UPDATE … WHERE status IN (PENDING, RETRY) AND available_at <= now`
  plus a lease (`lease_expires_at`). APScheduler fires the sweep generator at
  01:00 IST and the index computation after it.
* **Why:** Doc 16 names this the prototype target; it removes a broker from the
  demo, keeps retries/DLQ/idempotency in one transactional store, and survives
  worker restarts (expired leases are reclaimed). The stub `celery_app.py` /
  `tasks.py` were replaced; Celery can be reintroduced behind
  `packages/job_orchestration/queue.py` for the production target (doc 16 B)
  without touching adapters or the pipeline.
* **DLQ (doc 10):** jobs that exhaust `max_attempts`, or fail with a
  non-retryable error (parser error), move to status `FAILED` (doc 06 vocabulary) — the dead-letter
  set — and are re-queued manually via API/CLI.

## D2 — Raw evidence: content-addressed blob store + `raw_responses` + `raw_quotes`

* **Docs:** 02 §4 (raw payloads on S3/local disk referenced by `evidence_id`),
  03/07/08 (`raw_quotes.raw_payload` JSONB).
* **Choice:** both layers, because they serve different purposes:
  * `raw_responses` — one row per fetched response (URL, status, content type,
    SHA-256, size, fetch mode, latency). The body is stored in a
    content-addressed `EvidenceStore` (local filesystem in the prototype, S3
    compatible interface). `raw_responses.id` is the `evidence_id`.
  * `raw_quotes` — one row per fare the parser extracted, with the *unparsed*
    field strings in `raw_payload` (JSONB on Postgres, JSON on SQLite).
* **Why:** re-parsing needs the whole response (doc 07 “replay … without
  re-scraping”), while normalization replay needs per-quote raw strings.
  Lineage: `index_values → index_observations → normalized_quotes → raw_quotes →
  raw_responses → scrape_jobs → sources`.

## D3 — Money as `Decimal` rupees (`NUMERIC(12,2)`), not float or paise

The pre-existing Pydantic model used integer paise and the ORM used floats/ints
inconsistently. All monetary fields are `Decimal` INR with 2 dp end to end.

## D4 — Command-side vs query-side repositories

* **Docs:** 11 puts repositories in the API layer; 03/10 have the pipeline and
  workers writing to the same tables.
* **Choice:** `packages/domain/repositories/` holds write/lifecycle
  repositories used by the pipeline, orchestrator and index engine.
  `apps/api/repositories/` holds read-model queries used only by API services
  (pagination, analytics projections). API services never write raw/normalized
  data; they only enqueue jobs through the domain repositories.
* **Why:** packages must not import from `apps/`; keeping the split explicit
  avoids two competing data-access layers.

## D5 — `packages/scraping/fetchers` vs `packages/scraping/core/fetchers`

Both folders existed in the skeleton. Implementations live in
`core/fetchers/` (next to session, rate-limit, proxy — the engine internals).
`packages/scraping/fetchers/` is the public façade and the **fetcher factory**
that picks HTTP vs browser per source policy (doc 19 “swap between httpx and
Playwright … without changing the adapter”).

## D6 — New packages added to the skeleton

* `packages/config/` — centralised settings (`pydantic-settings`) and the
  reference data (basket, sources, carriers, fare classes) as YAML. No package
  in the skeleton owned configuration, and the brief requires it centralised.
* `packages/scraping/core/governance/` — robots.txt, source policy, block
  detection (doc 15 names a “Governance module”).
* `packages/scraping/core/resilience/` — retry policy and circuit breaker
  (docs 04, 10).

## D7 — Index methodology interpretation

* **Doc 09:** `APIx(d) = 100 · Σᵣ Wᵣ · (Pᵣd / Pᵣ0) · (Q0 / Qd)`, median
  elementary aggregates, LOCF imputation, DGCA weights, window sub-indices,
  weekly rolling average.
* **Implemented:**
  * Elementary aggregate = median `total_fare` of canonical, `VALID`,
    `AVAILABLE` quotes per (date, route, window).
  * Route price `Pᵣd` = window-weighted mean of the window medians; window
    weights are configurable (`index.window_weights`, default equal weights —
    no booking-curve weights are invented).
  * `Q` = mean hedonic quality factor of the fare classes in the cell;
    factors come from `fare_classes.yaml` (indicative, flagged as awaiting NSO
    input). `index.hedonic_adjustment=false` gives the pure Laspeyres value;
    both nominal and quality-adjusted values are always stored.
  * Base period = configurable date range; base prices are the mean of daily
    route prices in that range.
  * Weekly (ISO week) and monthly values = arithmetic mean of daily index
    values in the period (CPI period-average convention); a 7-day trailing
    rolling mean is also returned for the daily series.
  * Missing cells → LOCF up to `index.locf_max_days`, otherwise the route is
    dropped for that day and weights are re-normalised; imputed share and
    coverage are stored with every index value.
* The index engine is pure (no DB, no HTTP) — doc 09 “zero knowledge of the web
  scrapers”. It takes typed records rather than pandas DataFrames (same role,
  stricter typing, no heavy dependency).

## D8 — Simulated source for demo and backfill (clearly labelled synthetic)

Real sources cannot be scraped retroactively, yet ps.md asks for ≥30 days of
back-tested results and the demo must be reliable. A `simulated` source adapter
(`packages/scraping/sources/simulated/`) implements the **same** adapter
contract behind a `SimulatedFetcher` that returns JSON payloads from a
deterministic market model. Its quotes flow through the identical
raw → validation → normalization → dedup → index path. Everything it produces
carries `is_synthetic = true`; the API returns `data_origin`
(`live` / `simulated` / `mixed`) on every analytical response and the
dashboard shows a banner. It is enabled via `SAFAR_SIMULATED_SOURCE_ENABLED`.
This follows the earlier project decision recorded in commit `1a45c3d`
(“Deterministic simulation engine + real adapter stubs”).

## D9 — DGCA benchmark is external data

The backtest (`packages/index_engine/backtesting.py`) compares the monthly
APIx average fare against rows in `dgca_benchmarks`, loaded from a CSV
(`scripts/db/load_dgca_benchmark.py`). No DGCA numbers are shipped as if they
were real. The demo seeder can create a benchmark derived from the simulator
that is stored with `is_synthetic = true` and the label
“SYNTHETIC DEMO BENCHMARK — not DGCA data”; the API and UI surface that label.

## D10 — Real-source fixtures

Parser fixtures in `tests/fixtures/` for airline/OTA adapters are modelled on
the response structure each adapter targets; they are not claimed to be
verbatim captures. `scripts/scraper/capture_fixture.py` records real responses
(robots-checked, rate-limited) so fixtures can be replaced with genuine
captures, and `scripts/scraper/canary.py` is the nightly live regression check
from doc 14. Live sources ship `enabled: false` until their ToS/robots review
is recorded in `sources.yaml`.

## D11 — Dashboard

* **Docs:** 12 (React + Tailwind + Recharts, React Query polling FastAPI, no
  domain logic), 18 (`apps/dashboard`).
* The reference branch and the legacy root app (`src/`, Convex) compute the
  whole index client-side from a TypeScript simulator — that violates doc 12
  and is not reused as logic. The **visual design, page layout and chart
  components** are ported into `apps/dashboard` and rewired to the FastAPI
  endpoints. See "Reference branch reuse" below.

## D12 — Explicit distribution `channel` on sources

Cross-channel analysis (airline direct vs OTA convenience-fee wedge) needs to
know each source's channel. Real sources derive it from `kind`; the simulator
declares which channel it imitates (`simulated` = direct, `simulated_ota` =
OTA). Stored as `sources.channel`; the API never infers channels from ids.

## D13 — Shared parsers per payload family (no duplicated parsing logic)

IndiGo, Air India Express and Akasa run Navitaire dotREZ booking engines, so
they share `sources/common/navitaire.py`; the per-airline adapters only
declare search path, XHR pattern and URL parameters. OTAs and SpiceJet's
rendered results page share the declarative `sources/common/dom_cards.py`
(`CardSpec` with ordered selector fallbacks — doc 19 "adaptive selectors").
Air India (Amadeus DX style) has its own parser.

## D14 — Captured XHR endpoints are robots-checked too

The browser fetcher captures the JSON the *page* requests. Although the
crawler never requests that URL itself, the engine refuses capture when
robots.txt disallows the endpoint path. Consequence: SpiceJet (robots
disallows `/api/v1`) is read from the rendered page only.

## D15 — Index basket scope and coverage

The headline prices non-stop economy fares (`index.cabins`,
`index.include_connecting`); connections and premium cabins are stored and
queryable. A route enters a day's index only when all five purchase windows
are available (observed or LOCF-imputed), so the window mix cannot move the
route price. `coverage_pct` is the share of the *full* basket's route×window
cells actually observed that day — a partial collection is visible, not hidden.

## D16 — Amount parsing never guesses

`parse_money` accepts a plain amount or text with a rupee marker and exactly
one embedded amount (`"+ ₹349 convenience fee"`). No digits, several amounts
(`"₹4,999 or ₹5,499"`) or a non-rupee currency raise `CleaningError`; the
record is rejected with a reason instead of being stored as ₹0.

---

## Reference branch reuse (`origin/frontend-polish`)

| Reference component | What was reused | What was changed | Why |
|---|---|---|---|
| `scraper/safar/collect/base.py` `RobotsGate`, `TokenBucket`, `CHALLENGE_MARKERS` | Concepts: per-host robots cache with refresh, token bucket honouring Crawl-delay, challenge markers | Re-implemented in `core/governance` and `core/rate_limit` with async locks, injectable clock, fail-closed robots policy made configurable, tests | Fits doc 15; original had no tests and blocked the event loop (`rp.read()` is sync) |
| `src/convex/lib/basket.ts` 24-route basket, airports, carriers, sources, rate limits | Route list, distances, regions, indicative traffic weights, per-source rate limits | Moved to `packages/config/reference/*.yaml`; weights labelled *indicative* pending PSD/DGCA values | Doc 01 “Configuration driven by DGCA data” |
| `src/convex/lib/basket.ts` fare classes + quality scores | Fare-class taxonomy and indicative quality factors | YAML, flagged as awaiting NSO methodology | Doc 09 hedonic term needs factors |
| `api/main.py` `data_origin` flag | Idea of labelling synthetic vs live data in every response | Computed from `is_synthetic` lineage rather than hard-coded | Honesty in demo |
| `api/main.py` other endpoints | **Rejected** | — | Hard-coded responses (fake pipeline state, fake validation metrics) |
| `src/hooks/useApi.ts` | **Rejected** | Replaced by typed React Query client | Module-level mutable cache seeded with fake data |
| `src/convex/lib/engine.ts`, `index.ts` (client-side simulator/index) | **Rejected as logic** | Index lives in `packages/index_engine` | Doc 12: dashboard holds no domain logic |
| `src/pages/*`, `src/components/{AppShell,charts,neo}.tsx` | Visual direction, page structure, chart components | Ported to `apps/dashboard`, bound to FastAPI schemas | Doc 12 core views |
| `src/pages/Drivers.tsx` (ATF / USD-INR regression) | **Rejected** | — | Needs covariate data the system does not collect; not in ps.md |
| `src/pages/Deck.tsx`, `Auth.tsx`, `Landing.tsx` | **Rejected** | — | Presentation/auth for the Convex app; not part of doc 12 views |
