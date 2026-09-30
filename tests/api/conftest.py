"""A database populated through the production path, built once per test session.

9 observation days (26 Aug – 3 Sep 2026, spanning a month boundary) × 3 routes ×
5 purchase windows × 2 simulated channels → worker → index → synthetic
benchmark → back-test. Each test gets its own copy.
"""

from __future__ import annotations

import asyncio
import shutil
from collections.abc import Iterator
from datetime import date, timedelta
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from packages.config.reference import get_reference_data, reset_reference_data
from packages.config.settings import get_settings, reset_settings
from packages.domain.db import reset_engine, session_scope
from packages.domain.enums import SweepTrigger
from packages.domain.repositories.benchmarks import BenchmarkRepository
from packages.index_engine.backtest_service import BacktestService
from packages.index_engine.service import IndexService
from packages.job_orchestration.sweep import SweepGenerator, backfill_slot
from packages.job_orchestration.worker import Worker
from packages.scraping.sources.simulated.benchmark import synthetic_monthly_benchmark

START = date(2026, 8, 26)
DAYS = 9
ROUTES = ["DEL-BOM", "BLR-HYD", "DEL-BLR"]
API_KEY = "test-key-123"


def _reset() -> None:
    reset_settings()
    reset_reference_data()
    reset_engine()


@pytest.fixture(scope="session")
def populated_template(migrated_template: Path, tmp_path_factory: pytest.TempPathFactory) -> Path:
    root = tmp_path_factory.mktemp("populated")
    shutil.copy(migrated_template, root / "safar.db")
    with pytest.MonkeyPatch.context() as mp:
        mp.setenv("SAFAR_ENVIRONMENT", "test")
        mp.setenv("SAFAR_DATABASE_URL", f"sqlite:///{root / 'safar.db'}")
        mp.setenv("SAFAR_EVIDENCE_DIR", str(root / "evidence"))
        mp.setenv("SAFAR_SIMULATED_SOURCE_ENABLED", "true")
        mp.setenv("SAFAR_SCRAPING__BACKOFF_BASE_S", "0")
        mp.setenv("SAFAR_WORKER__POLL_INTERVAL_S", "0.01")
        _reset()
        settings, reference = get_settings(), get_reference_data()
        for i in range(DAYS):
            day = START + timedelta(days=i)
            with session_scope() as session:
                SweepGenerator(settings, reference).create(
                    session,
                    observation_date=day,
                    slot=backfill_slot(day),
                    trigger=SweepTrigger.BACKFILL,
                    routes=ROUTES,
                )
        asyncio.run(Worker(settings, reference).run(drain=True))
        with session_scope() as session:
            IndexService(settings, reference).compute(session)
        with session_scope() as session:
            BenchmarkRepository(session).upsert(
                synthetic_monthly_benchmark(reference, [date(2026, 8, 1), date(2026, 9, 1)])
            )
        with session_scope() as session:
            BacktestService().run(session)
        reset_engine()
    _reset()
    return root


@pytest.fixture
def api_env(populated_template: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    shutil.copy(populated_template / "safar.db", tmp_path / "safar.db")
    shutil.copytree(populated_template / "evidence", tmp_path / "evidence")
    monkeypatch.setenv("SAFAR_DATABASE_URL", f"sqlite:///{tmp_path / 'safar.db'}")
    monkeypatch.setenv("SAFAR_EVIDENCE_DIR", str(tmp_path / "evidence"))
    monkeypatch.setenv("SAFAR_API__API_KEYS", f'["{API_KEY}"]')
    _reset()
    return tmp_path


@pytest.fixture
def client(api_env: Path) -> Iterator[TestClient]:
    from apps.api.main import create_app

    with TestClient(create_app()) as test_client:
        yield test_client
