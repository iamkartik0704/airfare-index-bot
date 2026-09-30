"""End to end: source fixture → scrape → raw → normalize → DB → index → API → lineage.

Uses the IndiGo adapter (a *live* source type, so the API must report
``data_origin = live``) fed with the saved fixture through a scripted
transport — no network. Every governance, persistence and index step is the
production code path.
"""

from __future__ import annotations

import os
from datetime import date, timedelta
from pathlib import Path

import pytest
from alembic import command
from fastapi.testclient import TestClient
from sqlalchemy import update

from packages.config.reference import ReferenceData, get_reference_data, reset_reference_data
from packages.config.settings import Settings, get_settings, reset_settings
from packages.domain.db import reset_engine, session_scope
from packages.domain.enums import SweepTrigger
from packages.domain.models.database import Source
from packages.domain.repositories.jobs import JobRepository, JobSpec
from packages.domain.repositories.reference import routes_by_code, sync_reference_data
from packages.index_engine.service import IndexService
from packages.job_orchestration.sweep import SweepGenerator, backfill_slot
from packages.job_orchestration.worker import Worker
from packages.scraping.core.rate_limit.limiter import DomainRateLimiter
from packages.scraping.engine import ScrapeExecutor
from packages.scraping.fetchers import FetcherFactory
from tests.helpers import ScriptedFetcher, alembic_config, load_fixture, make_response, no_sleep, robots_gate

FIXTURE = load_fixture("json", "indigo", "availability_DEL_BOM_2026-10-07.json")
DAYS = [date(2026, 9, 28), date(2026, 9, 29), date(2026, 9, 30)]
WINDOWS = (1, 7, 15, 30, 45)


def _enqueue_indigo_days(reference: ReferenceData) -> None:
    with session_scope() as session:
        sync_reference_data(session, reference)
        session.execute(update(Source).where(Source.id == "indigo").values(enabled=True))
        route = routes_by_code(session)["DEL-BOM"]
        repo = JobRepository(session)
        for day in DAYS:
            sweep, _ = repo.get_or_create_sweep(
                slot=f"e2e:{day}", trigger=SweepTrigger.MANUAL, observation_date=day,
                parameters={}, requested_by="e2e",
            )
            repo.enqueue(
                sweep,
                [JobSpec("indigo", route.id, "DEL-BOM", day + timedelta(days=w), w) for w in WINDOWS],
                max_attempts=1,
            )


async def test_fixture_to_api_with_full_lineage(
    db: str, settings: Settings, reference: ReferenceData, monkeypatch: pytest.MonkeyPatch
) -> None:
    _enqueue_indigo_days(reference)
    fetcher = ScriptedFetcher([make_response(FIXTURE, content_type="application/json")])
    factory = FetcherFactory(settings.scraping)
    factory.register("browser", fetcher)
    executor = ScrapeExecutor(
        factory, settings.scraping, robots=robots_gate(),
        limiter=DomainRateLimiter(sleep=no_sleep), sleep=no_sleep,
    )
    stats = await Worker(settings, reference, fetchers=factory, executor=executor).run(drain=True)
    assert stats.by_status == {"SUCCESS": len(DAYS) * len(WINDOWS)}
    assert len(fetcher.requests) == len(DAYS) * len(WINDOWS)
    with session_scope() as session:
        summary = IndexService(settings, reference).compute(session)
    assert summary.latest_headline is not None

    monkeypatch.setenv("SAFAR_API__API_KEYS", '["e2e-key"]')
    reset_settings()
    from apps.api.main import create_app

    with TestClient(create_app()) as client:
        latest = client.get("/api/v1/index/latest").json()
        assert latest["data_origin"] == "live"  # a real-source adapter, not the simulator
        assert latest["date"] == DAYS[-1].isoformat()
        # Identical fixture every day → identical prices → index exactly 100.
        assert latest["value"] == "100.0000"
        # Coverage is over the whole basket: 1 of 24 routes was scraped.
        assert latest["coverage_pct"] == "4.17"

        # index value → elementary cells → canonical quotes …
        lineage = client.get(f"/api/v1/index/daily/{DAYS[-1].isoformat()}/lineage").json()
        assert {c["purchase_window"] for c in lineage["cells"] if c["route"] == "DEL-BOM"} == set(WINDOWS)
        quotes = client.get(lineage["quotes_endpoint"], params={"route": "DEL-BOM"}).json()["items"]
        # Saver + Flexi Plus (2 cards) + 6E6814 Saver, non-stop only in the index; 5 raw per job.
        assert {q["flight_number"] for q in quotes} >= {"6E2134", "6E6814"}

        # … → raw parser output → response → scrape job → exact evidence bytes.
        fare = next(q for q in quotes if q["flight_number"] == "6E2134" and q["fare_family"] == "Saver")
        detail = client.get(f"/api/v1/fares/{fare['id']}").json()
        assert detail["raw_payload"]["total_fare"] == "5263.00"
        assert detail["fare"]["total_fare"] == "5263.00"
        assert detail["parser"] == "indigo.IndigoAdapter@1"
        evidence = client.get(
            f"/api/v1/data/evidence/{detail['response_id']}", headers={"X-API-Key": "e2e-key"}
        )
        assert evidence.content == FIXTURE
        job = client.get(f"/api/v1/jobs/{detail['job_id']}").json()
        assert job["source_id"] == "indigo" and job["status"] == "SUCCESS"

        health = client.get("/api/v1/system/health").json()
        indigo = next(s for s in health["sources"] if s["id"] == "indigo")
        assert indigo["jobs_succeeded"] == len(DAYS) * len(WINDOWS) and indigo["status"] == "ACTIVE"


@pytest.mark.postgres
async def test_simulated_pipeline_on_postgres(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """The same production path on PostgreSQL (dialect-specific upserts, partial indexes, JSONB)."""
    url = os.environ["SAFAR_TEST_DATABASE_URL"]
    cfg = alembic_config(url)
    command.downgrade(cfg, "base")
    command.upgrade(cfg, "head")
    monkeypatch.setenv("SAFAR_DATABASE_URL", url)
    reset_settings()
    reset_reference_data()
    reset_engine()
    settings, reference = get_settings(), get_reference_data()
    for day in DAYS:
        with session_scope() as session:
            SweepGenerator(settings, reference).create(
                session, observation_date=day, slot=backfill_slot(day),
                trigger=SweepTrigger.BACKFILL, routes=["DEL-BOM", "BLR-HYD"],
            )
    stats = await Worker(settings, reference).run(drain=True)
    assert stats.processed == len(DAYS) * 2 * len(WINDOWS) * 2 and stats.crashed == 0
    with session_scope() as session:
        summary = IndexService(settings, reference).compute(session)
    assert summary.base_start == DAYS[0]
    with TestClient(__import__("apps.api.main", fromlist=["create_app"]).create_app()) as client:
        body = client.get("/api/v1/index/latest").json()
        assert body["data_origin"] == "simulated"
        assert client.get("/api/v1/analytics/channels").status_code == 200
    reset_engine()
