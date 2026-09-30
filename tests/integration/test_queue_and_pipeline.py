"""Job queue, raw store and pipeline against a migrated database."""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta

import pytest
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from packages.config.reference import ReferenceData
from packages.config.settings import Settings
from packages.data_pipeline.pipeline import NormalizationPipeline
from packages.domain.enums import FetchMode, JobStatus, QualityFlag, SweepTrigger
from packages.domain.models.database import NormalizedQuote, RawQuote, ScrapeJob, Source
from packages.domain.repositories.jobs import JobRepository
from packages.domain.repositories.raw import RawStoreRepository
from packages.domain.repositories.reference import routes_by_code, sync_reference_data
from packages.domain.exceptions import ConfigurationError
from packages.job_orchestration.sweep import SweepGenerator

OBS = date(2026, 9, 30)


def make_sweep(session: Session, settings: Settings, reference: ReferenceData, **kw: object) -> ScrapeJob:
    SweepGenerator(settings, reference).create(
        session,
        observation_date=OBS,
        slot=str(kw.pop("slot", "slot-1")),
        trigger=SweepTrigger.MANUAL,
        routes=["DEL-BOM"],
        windows=(7,),
        sources=["simulated"],
    )
    session.flush()
    return session.scalars(select(ScrapeJob)).first()  # type: ignore[return-value]


class TestReferenceSync:
    def test_sync_is_idempotent_and_preserves_runtime_status(
        self, session: Session, reference: ReferenceData
    ) -> None:
        sync_reference_data(session, reference)
        source = session.get(Source, "indigo")
        assert source is not None
        source.consecutive_failures = 4
        sync_reference_data(session, reference)
        assert session.get(Source, "indigo").consecutive_failures == 4  # type: ignore[union-attr]
        assert len(routes_by_code(session)) == len(reference.basket.routes)


class TestJobQueue:
    def test_sweep_fan_out_and_idempotent_enqueue(
        self, session: Session, settings: Settings, reference: ReferenceData
    ) -> None:
        gen = SweepGenerator(settings, reference)
        first = gen.create(session, observation_date=OBS, slot="s", trigger=SweepTrigger.MANUAL)
        again = gen.create(session, observation_date=OBS, slot="s", trigger=SweepTrigger.MANUAL)
        # 24 routes × 5 windows × 2 simulated sources
        assert first.jobs_enqueued == 240 and first.created
        assert again.jobs_enqueued == 0 and not again.created
        windows = set(session.scalars(select(ScrapeJob.purchase_window)))
        assert windows == {1, 7, 15, 30, 45}
        job = session.scalars(select(ScrapeJob).where(ScrapeJob.purchase_window == 15)).first()
        assert job is not None and job.travel_date == OBS + timedelta(days=15)

    def test_backfill_refuses_real_sources(
        self, session: Session, settings: Settings, reference: ReferenceData
    ) -> None:
        with pytest.raises(ConfigurationError):
            SweepGenerator(settings, reference).create(
                session, observation_date=OBS, slot="b", trigger=SweepTrigger.BACKFILL, sources=["indigo"]
            )

    def test_claim_is_exclusive_and_respects_source_concurrency(
        self, session: Session, settings: Settings, reference: ReferenceData
    ) -> None:
        SweepGenerator(settings, reference).create(
            session, observation_date=OBS, slot="c", trigger=SweepTrigger.MANUAL, sources=["simulated"]
        )
        repo = JobRepository(session)
        first = repo.claim(worker_id="w1", limit=10, lease_seconds=60)
        assert len(first) == 3  # simulated max_concurrency = 3
        assert repo.claim(worker_id="w2", limit=10, lease_seconds=60) == []
        assert all(j.status is JobStatus.RUNNING and j.attempts == 1 for j in first)

    def test_expired_leases_are_recovered_then_dead_lettered(
        self, session: Session, settings: Settings, reference: ReferenceData
    ) -> None:
        job = make_sweep(session, settings, reference)
        repo = JobRepository(session)
        now = datetime.now(UTC)
        for attempt in range(1, job.max_attempts + 1):
            [claimed] = repo.claim(worker_id="w", limit=1, lease_seconds=1, now=now)
            assert claimed.attempts == attempt
            now += timedelta(seconds=5)
            assert repo.recover_expired_leases(now) == 1
        assert job.status is JobStatus.FAILED and job.last_error_code == "lease_expired"
        assert repo.requeue([job.id]) == 1
        assert job.status is JobStatus.PENDING and job.attempts == 0

    def test_failure_policy_retry_vs_terminal(
        self, session: Session, settings: Settings, reference: ReferenceData
    ) -> None:
        job = make_sweep(session, settings, reference)
        repo = JobRepository(session)
        [claimed] = repo.claim(worker_id="w", limit=1, lease_seconds=60)
        status = repo.mark_failure(claimed, code="timeout", message="slow", retryable=True, retry_in=30)
        assert status is JobStatus.RETRY and claimed.available_at > datetime.now(UTC)
        status = repo.mark_failure(claimed, code="parse_error", message="bad", retryable=False, retry_in=0)
        assert status is JobStatus.FAILED


def store_raw(session: Session, job: ScrapeJob, payloads: list[dict[str, str]], observed_at: datetime) -> None:
    raw = RawStoreRepository(session)
    response = raw.save_response(
        job, url="sim://market/search", method="GET", fetch_mode=FetchMode.SIMULATED,
        status_code=200, content_type="application/json", sha256=f"{observed_at.timestamp():064.0f}"[-64:],
        byte_size=10, storage_uri="evidence://x", duration_ms=1, fetched_at=observed_at,
        blocked=False, block_reason=None,
    )
    raw.save_quotes(
        [
            {
                "job_id": job.id, "response_id": response.id, "source_id": job.source_id,
                "route_id": job.route_id, "observation_date": job.observation_date,
                "travel_date": job.travel_date, "purchase_window": job.purchase_window,
                "observed_at": observed_at, "record_index": i, "raw_payload": p,
                "parser_name": "test", "parser_version": "1", "created_at": observed_at,
            }
            for i, p in enumerate(payloads)
        ]
    )


def card(flight: str, total: int, family: str = "Saver") -> dict[str, str]:
    return {
        "carrier": "IndiGo", "flight_number": flight, "fare_class": family,
        "total_fare": f"₹{total:,}", "availability": "AVAILABLE", "stops": "Non-stop",
    }


class TestPipeline:
    def test_raw_to_normalized_with_dedup_outliers_and_lineage(
        self, session: Session, settings: Settings, reference: ReferenceData
    ) -> None:
        job = make_sweep(session, settings, reference)
        t0 = datetime(2026, 9, 30, 1, tzinfo=UTC)
        payloads = [card(f"6E {100 + i}", 5000 + 20 * i) for i in range(6)]
        payloads.append(card("6E 100", 5010))  # duplicated listing of the first card
        payloads.append(card("6E 999", 52000))  # garbled price
        payloads.append({"carrier": "Unknown Air", "flight_number": "ZZ1", "total_fare": "₹1"})
        store_raw(session, job, payloads, t0)
        pipeline = NormalizationPipeline(reference, settings.quality)
        report = pipeline.process_job(session, job)
        assert report.raw == 9 and report.normalized == 8
        assert report.rejected == {"unknown carrier": 1}
        assert report.duplicates == 1 and report.outliers == 1
        rows = session.scalars(select(NormalizedQuote)).all()
        flags = {r.flight_number: r.quality_flag for r in rows if r.quality_flag is not QualityFlag.DUPLICATE}
        assert flags["6E999"] is QualityFlag.OUTLIER
        assert all(r.raw_quote_id is not None and r.job_id == job.id for r in rows)
        # Lineage: normalized → raw → response → job
        sample = rows[0]
        raw = session.get(RawQuote, sample.raw_quote_id)
        assert raw is not None and raw.response.job_id == job.id

        # Idempotent: processing the same job again adds nothing.
        again = pipeline.process_job(session, job)
        assert again.normalized == 0 and again.already_normalized == 9 - 1
        assert session.scalar(select(func.count()).select_from(NormalizedQuote)) == 8

    def test_later_observation_supersedes_earlier(
        self, session: Session, settings: Settings, reference: ReferenceData
    ) -> None:
        job = make_sweep(session, settings, reference)
        pipeline = NormalizationPipeline(reference, settings.quality)
        t0 = datetime(2026, 9, 30, 1, tzinfo=UTC)
        store_raw(session, job, [card("6E 100", 5000)], t0)
        pipeline.process_job(session, job)
        store_raw(session, job, [card("6E 100", 5600)], t0 + timedelta(hours=6))
        report = pipeline.process_job(session, job)
        assert report.superseded == 1
        live = session.scalars(
            select(NormalizedQuote).where(NormalizedQuote.quality_flag != QualityFlag.DUPLICATE)
        ).all()
        assert [r.total_fare for r in live] == [5600]
        assert live[0].is_canonical

    def test_rebuild_regenerates_from_raw(
        self, session: Session, settings: Settings, reference: ReferenceData
    ) -> None:
        job = make_sweep(session, settings, reference)
        store_raw(session, job, [card("6E 1", 5000), card("6E 2", 5100)], datetime(2026, 9, 30, tzinfo=UTC))
        pipeline = NormalizationPipeline(reference, settings.quality)
        pipeline.process_job(session, job)
        report = pipeline.process_job(session, job, rebuild=True)
        assert report.normalized == 2 and report.already_normalized == 0
        assert session.scalar(select(func.count()).select_from(RawQuote)) == 2

    def test_live_dedup_key_is_unique_in_the_database(
        self, session: Session, settings: Settings, reference: ReferenceData
    ) -> None:
        job = make_sweep(session, settings, reference)
        store_raw(session, job, [card("6E 1", 5000), card("6E 2", 5100)], datetime(2026, 9, 30, tzinfo=UTC))
        NormalizationPipeline(reference, settings.quality).process_job(session, job)
        first, second = session.scalars(select(NormalizedQuote).order_by(NormalizedQuote.id)).all()
        second.dedup_key = first.dedup_key  # two live rows for one fare: forbidden
        with pytest.raises(IntegrityError):
            session.flush()
