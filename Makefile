# Developer commands for the SAFAR backend. Requires uv (https://docs.astral.sh/uv/).
PY := .venv/bin

.PHONY: setup migrate api worker scheduler demo test test-pg lint format typecheck check dashboard up down

setup:            ## create .venv and install backend + dev + browser deps
	uv venv --python 3.12 .venv
	uv pip install --python $(PY)/python -e '.[dev,browser]'

migrate:          ## apply database migrations (the only way the schema is created)
	$(PY)/alembic upgrade head

api:              ## run the FastAPI server on :8000
	$(PY)/uvicorn apps.api.main:app --reload --port 8000

worker:           ## run a scrape worker (claims jobs from the DB queue)
	$(PY)/safar worker

scheduler:        ## run the cron scheduler (01:00 IST sweep, 06:30 IST index)
	$(PY)/safar scheduler

demo:             ## migrate + 35 days of SIMULATED data → index → synthetic back-test
	$(PY)/alembic upgrade head
	SAFAR_SIMULATED_SOURCE_ENABLED=true $(PY)/safar demo --days 35

test:             ## full test suite (SQLite)
	$(PY)/pytest

test-pg:          ## tests marked `postgres` against SAFAR_TEST_DATABASE_URL
	$(PY)/pytest -m postgres

format:
	$(PY)/ruff format packages apps/api scripts tests infrastructure/db

lint:
	$(PY)/ruff check packages apps/api scripts tests infrastructure/db

typecheck:
	$(PY)/mypy

check: lint typecheck test

dashboard:        ## run the dashboard dev server on :5173 (proxies /api to :8000)
	cd apps/dashboard && npm install && npm run dev

up:               ## full stack in Docker (needs .env)
	docker compose up --build -d

down:
	docker compose down
