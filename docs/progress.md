# Progress

Milestones follow `docs/architecture/17-implementation-roadmap.md`.

- [x] Stage 0 — repository foundation (`pyproject.toml`, uv venv, ruff/mypy/pytest config, `packages/config`)
- [x] Stage 1 — canonical domain models (Pydantic + SQLAlchemy + Alembic migration `0001`)
- [x] Stage 2 — scraping core (fetchers, governance/robots, blocks, rate limit, retry, circuit breaker, engine)
- [x] Stage 3 — first airline (IndiGo XHR adapter + fixtures) and the simulated source (D8)
- [x] Stage 4 — raw storage (evidence store, raw_responses/raw_quotes) & normalization pipeline
- [x] Stage 5 — scheduling (DB job queue, worker, APScheduler, `safar` CLI)
- [x] Stage 6 — index engine (Laspeyres + hedonic, LOCF, D/W/M, analytics, backtest core)
- [ ] Stage 7 — API & dashboard
- [ ] Stage 8 — additional sources (Air India, MakeMyTrip, …)
- [ ] Stage 9 — backtesting & validation (service + CLI done; API/UI pending)
- [ ] Final verification & compliance review

## Log

### 2026-09-30 — Inspection
* Read ps.md, all `docs/architecture/*`, existing packages, reference branch `origin/frontend-polish`.
* Wrote `docs/implementation-status.md` (requirement map) and `docs/decisions.md`.

### 2026-09-30 — Stages 0–6
* Replaced stub packages with working implementations (see `docs/implementation-status.md`).
* Removed duplicate/stub modules: `packages/data_pipeline/models/db.py` (second ORM),
  `normalization/etl.py`, `validation/validator.py`, `job_orchestration/{celery_app,tasks}.py` (D1).
* Legacy unit tests targeting removed stub APIs were replaced by tests of the new
  modules; their scenarios were ported (see `docs/test-status.md`).
* Verified: 10-day simulated backfill → 2,400 jobs → 55k canonical quotes → index.
* Migration verified on SQLite and PostgreSQL 16 (upgrade, `alembic check`, downgrade).

## Next action
Stage 7: FastAPI app (`apps/api`) — routers → services → repositories, schemas,
error handling, API-key dependency, `/metrics`; then the dashboard.
