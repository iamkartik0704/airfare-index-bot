"""Worker failure policies, source health/circuit, index service, migrations."""

from __future__ import annotations

from datetime import date

import pytest
from alembic import command
from sqlalchemy import create_engine, func, inspect, select, update
from sqlalchemy.orm import Session

from packages.config.reference import ReferenceData
from packages.config.settings import Settings
from packages.domain.db import session_scope
from packages.domain.enums import JobStatus, RunStatus, SourceStatus, SweepStatus, SweepTrigger
from packages.domain.models.database import (
    IndexRun,
    IndexValueRow,
    NormalizedQuote,
    RawResponse,
    ScrapeJob,
    Source,
    SourceHealth,
    Sweep,
)
from packages.domain.repositories.jobs import JobRepository, JobSpec
from packages.domain.repositories.reference import routes_by_code, sync_reference_data
from packages.index_engine.exceptions import InsufficientDataError
from packages.index_engine.service import IndexService
from packages.job_orchestration.sweep import SweepGenerator
from packages.job_orchestration.worker import Worker
from packages.scraping.core.rate_limit.limiter import DomainRateLimiter
from packages.scraping.core.resilience.retry import RetryPolicy
from packages.scraping.engine import ScrapeExecutor
from packages.scraping.fetchers import FetcherFactory
from tests.helpers import ScriptedFetcher, alembic_config, load_fixture, make_response, no_sleep, robots_gate

OBS = date(2026, 9, 30)
INDIGO_OK = load_fixture("json", "indigo", "availability_DEL_BOM_2026-10-07.json")


def enqueue_indigo(n_jobs: int = 1) -> None:
    with session_scope() as session:
        from packages.config.reference import get_reference_data

        sync_reference_data(session, get_reference_data())
        session.execute(update(Source).where(Source.id == "indigo").values(enabled=True))
        route = routes_by_code(session)["DEL-BOM"]
        repo = JobRepository(session)
        sweep, _ = repo.get_or_create_sweep(
            slot="t", trigger=SweepTrigger.MANUAL, observation_date=OBS, parameters={}, requested_by="test"
        )
        specs = [
            JobSpec("indigo", route.id, "DEL-BOM", date(2026, 10, 7 + i), 7 + i) for i in range(n_jobs)
        ]
        repo.enqueue(sweep, specs, max_attempts=2)


def worker_with(settings: Settings, reference: ReferenceData, fetcher: ScriptedFetcher) -> Worker:
    factory = FetcherFactory(settings.scraping)
    factory.register("browser", fetcher)
    executor = ScrapeExecutor(
        factory,
        settings.scraping,
        robots=robots_gate(),
        limiter=DomainRateLimiter(sleep=no_sleep),
        retry=RetryPolicy(max_attempts=1),
        sleep=no_sleep,
    )
    return Worker(settings, reference, fetchers=factory, executor=executor)


def jobs(session: Session) -> list[ScrapeJob]:
    return list(session.scalars(select(ScrapeJob).order_by(ScrapeJob.travel_date)))


class TestWorkerPolicies:
    async def test_success_stores_evidence_raw_and_normalized(
        self, db: str, settings: Settings, reference: ReferenceData
    ) -> None:
        enqueue_indigo()
        fetcher = ScriptedFetcher([make_response(INDIGO_OK, content_type="application/json")])
        stats = await worker_with(settings, reference, fetcher).run(drain=True)
        assert stats.by_status == {"SUCCESS": 1}
        with session_scope() as session:
            [job] = jobs(session)
            assert job.status is JobStatus.SUCCESS and job.items_scraped == 5
            [response] = session.scalars(select(RawResponse)).all()
            assert response.storage_uri.startswith("evidence://") and not response.blocked
            assert session.scalar(select(func.count()).select_from(NormalizedQuote)) == 5
            health = session.scalars(select(SourceHealth).where(SourceHealth.source_id == "indigo")).one()
            assert health.jobs_succeeded == 1 and health.quotes_collected == 5
            assert health.status_codes == {"200": 1}
            assert session.scalar(select(Sweep.status)) is SweepStatus.COMPLETED

    async def test_block_marks_source_blocked_and_skips_remaining_jobs(
        self, db: str, settings: Settings, reference: ReferenceData
    ) -> None:
        settings.worker.concurrency = 1
        enqueue_indigo(n_jobs=2)
        fetcher = ScriptedFetcher([make_response("<html><title>Access Denied</title></html>", status=200)])
        stats = await worker_with(settings, reference, fetcher).run(drain=True)
        assert stats.by_status == {"FAILED": 1, "SKIPPED": 1}
        assert len(fetcher.requests) == 1  # never retried, never bypassed
        with session_scope() as session:
            source = session.get(Source, "indigo")
            assert source is not None and source.status is SourceStatus.BLOCKED
            assert source.circuit_open_until is not None
            first, second = jobs(session)
            assert first.last_error_code == "source_blocked"
            assert second.status is JobStatus.SKIPPED and second.last_error_code == "circuit_open"
            assert session.scalar(select(RawResponse.blocked)) is True  # evidence of the block kept

    async def test_parse_error_goes_to_dead_letter(
        self, db: str, settings: Settings, reference: ReferenceData
    ) -> None:
        enqueue_indigo()
        fetcher = ScriptedFetcher([make_response(load_fixture("json", "indigo", "availability_schema_changed.json"), content_type="application/json")])
        await worker_with(settings, reference, fetcher).run(drain=True)
        with session_scope() as session:
            [job] = jobs(session)
            assert job.status is JobStatus.FAILED and job.last_error_code == "parse_error"
            health = session.scalars(select(SourceHealth)).one()
            assert health.parse_errors == 1
            assert session.get(Source, "indigo").consecutive_failures == 1  # type: ignore[union-attr]

    async def test_network_failure_retries_then_opens_circuit(
        self, db: str, settings: Settings, reference: ReferenceData
    ) -> None:
        settings.scraping.circuit_failure_threshold = 2
        settings.worker.concurrency = 1
        enqueue_indigo(n_jobs=3)
        fetcher = ScriptedFetcher([make_response("oops", status=500)])
        await worker_with(settings, reference, fetcher).run(drain=True)
        with session_scope() as session:
            source = session.get(Source, "indigo")
            assert source is not None and source.status is SourceStatus.DEGRADED
            statuses = [j.status for j in jobs(session)]
            assert JobStatus.SKIPPED in statuses  # later jobs skipped while the circuit is open
            # The two failing attempts are counted even though the jobs ended SKIPPED.
            assert sum(j.errors_encountered for j in jobs(session)) == 2

    async def test_robots_disallow_skips_without_requests(
        self, db: str, settings: Settings, reference: ReferenceData
    ) -> None:
        enqueue_indigo()
        fetcher = ScriptedFetcher([make_response(INDIGO_OK)])
        worker = worker_with(settings, reference, fetcher)
        worker._runner._executor._robots = robots_gate("User-agent: *\nDisallow: /booking")  # type: ignore[attr-defined]
        await worker.run(drain=True)
        assert fetcher.requests == []
        with session_scope() as session:
            [job] = jobs(session)
            assert job.status is JobStatus.SKIPPED and job.last_error_code == "robots_disallowed"
            assert session.scalars(select(SourceHealth)).one().robots_denied == 1


class TestSimulatedSweepToIndex:
    async def test_two_days_of_simulated_data_produce_an_index(
        self, db: str, settings: Settings, reference: ReferenceData
    ) -> None:
        for day in (date(2026, 9, 1), date(2026, 9, 2)):
            with session_scope() as session:
                SweepGenerator(settings, reference).create(
                    session, observation_date=day, slot=f"bf:{day}", trigger=SweepTrigger.BACKFILL,
                    routes=["DEL-BOM", "BLR-HYD", "DEL-BLR"],
                )
        stats = await Worker(settings, reference).run(drain=True)
        assert stats.by_status.get("SUCCESS") == stats.processed == 60
        with session_scope() as session:
            summary = IndexService(settings, reference).compute(session)
        assert summary.base_start == date(2026, 9, 1)
        with session_scope() as session:
            run = session.get(IndexRun, summary.run_id)
            assert run is not None and run.status is RunStatus.SUCCESS
            assert run.parameters["basket_status"] == "INDICATIVE"
            assert "routes" in run.parameters["weights"]
            values = session.scalars(select(IndexValueRow).where(IndexValueRow.scope == "HEADLINE")).all()
            assert {v.frequency.value for v in values} == {"DAILY", "WEEKLY", "MONTHLY"}
            assert all(v.is_synthetic for v in values)

    def test_index_without_data_records_failure(self, db: str, settings: Settings, reference: ReferenceData) -> None:
        with pytest.raises(InsufficientDataError), session_scope() as session:
            IndexService(settings, reference).compute(session)


class TestMigrations:
    def test_fresh_database_matches_models(self, tmp_path) -> None:  # type: ignore[no-untyped-def]
        url = f"sqlite:///{tmp_path / 'fresh.db'}"
        cfg = alembic_config(url)
        command.upgrade(cfg, "head")
        command.check(cfg)  # raises if models and migrations diverge
        tables = set(inspect(create_engine(url)).get_table_names())
        assert {"raw_quotes", "normalized_quotes", "index_values", "dgca_benchmarks"} <= tables
        command.downgrade(cfg, "base")
        assert set(inspect(create_engine(url)).get_table_names()) <= {"alembic_version"}

    @pytest.mark.postgres
    def test_postgres_upgrade_and_check(self) -> None:
        import os

        cfg = alembic_config(os.environ["SAFAR_TEST_DATABASE_URL"])
        command.downgrade(cfg, "base")
        command.upgrade(cfg, "head")
        command.check(cfg)
