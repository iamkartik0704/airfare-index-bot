"""System console: health, sources, freshness, jobs, sweeps, backtests, methodology."""

from __future__ import annotations

import uuid
from datetime import date, timedelta

from sqlalchemy.orm import Session

from apps.api.repositories.system_read import SystemReadRepository
from apps.api.schemas.common import Page
from apps.api.schemas.operations import (
    BacktestOut,
    BacktestPointOut,
    BenchmarkOut,
    Freshness,
    HealthBucketOut,
    JobOut,
    Methodology,
    RequeueResult,
    SourceHealthOut,
    SweepCreated,
    SweepOut,
    SweepRequest,
    SystemHealth,
)
from packages.config.reference import ReferenceData
from packages.config.settings import Settings
from packages.domain.enums import JobStatus, SourceStatus, SweepStatus, SweepTrigger
from packages.domain.exceptions import NotFoundError
from packages.domain.models.database import ScrapeJob, Source, utcnow
from packages.domain.repositories.benchmarks import BenchmarkRepository
from packages.domain.repositories.health import SourceHealthRepository
from packages.domain.repositories.index import IndexRepository
from packages.domain.repositories.jobs import JobRepository
from packages.job_orchestration.sweep import SweepGenerator, manual_slot
from packages.scraping.sources.registry import is_runnable

WINDOW_HOURS = 24


def job_out(job: ScrapeJob, route: str) -> JobOut:
    return JobOut(
        id=job.id,
        sweep_id=job.sweep_id,
        source_id=job.source_id,
        route=route,
        observation_date=job.observation_date,
        travel_date=job.travel_date,
        purchase_window=job.purchase_window,
        status=job.status,
        attempts=job.attempts,
        max_attempts=job.max_attempts,
        items_scraped=job.items_scraped,
        errors_encountered=job.errors_encountered,
        last_error_code=job.last_error_code,
        last_error_message=job.last_error_message,
        started_at=job.started_at,
        completed_at=job.completed_at,
    )


class SystemService:
    def __init__(self, session: Session, settings: Settings, reference: ReferenceData) -> None:
        self.session = session
        self.repo = SystemReadRepository(session)
        self.settings = settings
        self.reference = reference

    # ------------------------------------------------------------------ health

    def _source_out(self, source: Source, counters: dict[str, int]) -> SourceHealthOut:
        definition = next((s for s in self.reference.sources if s.id == source.id), None)
        done = counters.get("jobs_succeeded", 0) + counters.get("jobs_failed", 0)
        requests = counters.get("requests", 0)
        return SourceHealthOut(
            id=source.id,
            name=source.name,
            kind=source.kind,
            enabled=source.enabled,
            runnable=bool(definition and is_runnable(definition, self.settings)),
            is_synthetic=source.is_synthetic,
            tos_reviewed=source.tos_reviewed,
            status=source.status,
            status_reason=source.status_reason,
            circuit_open_until=source.circuit_open_until,
            consecutive_failures=source.consecutive_failures,
            last_success_at=source.last_success_at,
            rate_limit_rpm=source.rate_limit_rpm,
            crawl_delay_s=source.crawl_delay_s,
            window_hours=WINDOW_HOURS,
            requests=requests,
            jobs_succeeded=counters.get("jobs_succeeded", 0),
            jobs_failed=counters.get("jobs_failed", 0),
            blocked=counters.get("blocked", 0),
            rate_limited=counters.get("rate_limited", 0),
            parse_errors=counters.get("parse_errors", 0),
            robots_denied=counters.get("robots_denied", 0),
            quotes_collected=counters.get("quotes_collected", 0),
            success_rate=round(counters.get("jobs_succeeded", 0) / done, 4) if done else None,
            avg_latency_ms=round(counters.get("total_latency_ms", 0) / requests, 1)
            if requests
            else None,
        )

    def sources(self) -> list[SourceHealthOut]:
        window = SourceHealthRepository(self.session).window(
            utcnow() - timedelta(hours=WINDOW_HOURS)
        )
        return [self._source_out(s, window.get(s.id, {})) for s in self.repo.sources()]

    def source_buckets(self, source_id: str, hours: int) -> list[HealthBucketOut]:
        if self.session.get(Source, source_id) is None:
            raise NotFoundError("unknown source", source=source_id)
        return [
            HealthBucketOut.model_validate(b, from_attributes=True)
            for b in SourceHealthRepository(self.session).recent_buckets(source_id, hours)
        ]

    def freshness(self) -> Freshness:
        observed_at, observed_date = self.repo.newest_observation()
        index_date, index_at = self.repo.latest_index()
        age = (utcnow() - observed_at).total_seconds() if observed_at else None
        return Freshness(
            latest_observation_at=observed_at,
            latest_observation_date=observed_date,
            age_seconds=age,
            stale=age is None or age > self.settings.api.stale_after_hours * 3600,
            latest_index_date=index_date,
            latest_index_run_at=index_at,
        )

    def health(self) -> SystemHealth:
        self.repo.ping()
        sources = self.sources()
        freshness = self.freshness()
        runnable = [s for s in sources if s.runnable]
        unhealthy = [s for s in runnable if s.status is not SourceStatus.ACTIVE]
        if not runnable or (unhealthy and len(unhealthy) == len(runnable)):
            status = "down"
        elif unhealthy or freshness.stale:
            status = "degraded"
        else:
            status = "ok"
        return SystemHealth(
            status=status,
            database="ok",
            freshness=freshness,
            queue=self.repo.queue_counts(),
            sources=sources,
        )

    # ------------------------------------------------------------------ jobs & sweeps

    def jobs(
        self,
        status: JobStatus | None,
        source: str | None,
        sweep_id: uuid.UUID | None,
        limit: int,
        offset: int,
    ) -> Page[JobOut]:
        rows, total = self.repo.jobs(
            status=status, source=source, sweep_id=sweep_id, limit=limit, offset=offset
        )
        return Page[JobOut](
            items=[job_out(j, c) for j, c in rows], total=total, limit=limit, offset=offset
        )

    def job(self, job_id: uuid.UUID) -> JobOut:
        found = self.repo.job(job_id)
        if found is None:
            raise NotFoundError("job not found", job_id=str(job_id))
        return job_out(*found)

    def requeue(self, job_ids: list[uuid.UUID]) -> RequeueResult:
        return RequeueResult(requeued=JobRepository(self.session).requeue(job_ids))

    def sweeps(self, status: SweepStatus | None, limit: int, offset: int) -> Page[SweepOut]:
        rows, total = self.repo.sweeps(status=status, limit=limit, offset=offset)
        counts = self.repo.job_counts_for([s.id for s in rows])
        items = [
            SweepOut(
                id=s.id,
                slot=s.slot,
                trigger_type=s.trigger_type,
                observation_date=s.observation_date,
                status=s.status,
                jobs_total=s.jobs_total,
                created_at=s.created_at,
                completed_at=s.completed_at,
                job_counts=counts.get(s.id, {}),
            )
            for s in rows
        ]
        return Page[SweepOut](items=items, total=total, limit=limit, offset=offset)

    def create_sweep(self, request: SweepRequest) -> SweepCreated:
        result = SweepGenerator(self.settings, self.reference).create(
            self.session,
            observation_date=request.observation_date or date.today(),
            slot=manual_slot(),
            trigger=SweepTrigger.MANUAL,
            requested_by="api",
            sources=request.sources,
            routes=request.routes,
            windows=tuple(request.windows) if request.windows else None,
        )
        return SweepCreated(
            sweep_id=result.sweep_id,
            slot=result.slot,
            jobs_enqueued=result.jobs_enqueued,
            jobs_total=result.jobs_total,
        )

    # ------------------------------------------------------------------ backtests & methodology

    def latest_backtest(self) -> BacktestOut:
        run = BenchmarkRepository(self.session).latest_run()
        if run is None:
            raise NotFoundError("no back-test has been run yet")
        return BacktestOut(
            id=run.id,
            created_at=run.created_at,
            period_start=run.period_start,
            period_end=run.period_end,
            days_covered=run.days_covered,
            benchmark_label=run.benchmark_label,
            benchmark_is_synthetic=run.benchmark_is_synthetic,
            apix_is_synthetic=run.apix_is_synthetic,
            metrics=run.metrics,
            verdict=run.verdict,
            points=[BacktestPointOut.model_validate(p, from_attributes=True) for p in run.points],
        )

    def benchmarks(self) -> list[BenchmarkOut]:
        return [
            BenchmarkOut.model_validate(b, from_attributes=True)
            for b in BenchmarkRepository(self.session).monthly("ALL")
        ]

    def methodology(self) -> Methodology:
        run = IndexRepository(self.session).latest_run()
        params = run.parameters if run else {}
        base = (
            (run.base_period_start, run.base_period_end)
            if run and run.base_period_start and run.base_period_end
            else None
        )
        weights = self.reference.basket.normalized_weights()
        idx = self.settings.index
        windows = list(self.settings.scheduler.purchase_windows)
        window_weights = params.get("weights", {}).get("windows") or {
            str(w): str(round(1 / len(windows), 6)) for w in windows
        }
        return Methodology(
            formula="APIx(d) = 100 · Σr Wr · (Pr,d / Pr,0) · (Q0 / Qd)",
            description=[
                "Elementary aggregate: median total fare of canonical, valid, available, "
                "non-stop economy quotes per (date, route, purchase window).",
                "Route price Pr,d: window-weighted mean of the window medians; a route is priced "
                "only when every purchase window is available (observed or LOCF-imputed).",
                "Base period prices Pr,0 and quality Q0: means over the base period.",
                "Q: weighted mean hedonic quality factor of the fare classes observed (doc 09).",
                "Weekly and monthly values: averages of the daily index.",
                f"Missing cells: last observation carried forward for up to "
                f"{idx.locf_max_days} days.",
            ],
            basket={
                "version": self.reference.basket.version,
                "status": self.reference.basket.status,
                "weights_source": self.reference.basket.weights_source,
                "routes": [
                    {
                        "code": r.code,
                        "region": r.region,
                        "distance_km": r.distance_km,
                        "weight": str(r.weight),
                        "weight_share_pct": str(round(100 * weights[r.code], 3)),
                    }
                    for r in self.reference.basket.routes
                ],
            },
            fare_classes={
                "status": self.reference.fare_classes.status,
                "note": self.reference.fare_classes.note,
                "classes": [
                    {
                        "code": c.code,
                        "label": c.label,
                        "cabin": c.cabin,
                        "quality_factor": str(c.quality_factor),
                    }
                    for c in self.reference.fare_classes.classes
                ],
            },
            purchase_windows=windows,
            window_weights={str(k): str(v) for k, v in window_weights.items()},
            hedonic_adjustment=idx.hedonic_adjustment,
            base_period=base,
            base_period_source=params.get("base_period_source"),
            cabins=list(idx.cabins),
            include_connecting=idx.include_connecting,
            quality_rules={
                "mad_threshold": self.settings.quality.mad_threshold,
                "min_group_size_for_mad": self.settings.quality.min_group_size_for_mad,
                "fare_floor_inr": self.settings.quality.fare_floor_inr,
                "fare_ceiling_inr": self.settings.quality.fare_ceiling_inr,
                "total_tolerance_inr": self.settings.quality.total_tolerance_inr,
                "dedup": "latest observation per source/flight/fare family/day wins; "
                "airline-direct preferred across channels",
            },
            external_dependencies=[
                "Official route basket and weights (ps.md: 'PSD given routes and weights') — "
                f"current basket status: {self.reference.basket.status}",
                "NSO hedonic methodology / fare-class quality factors — "
                f"current status: {self.reference.fare_classes.status}",
                "DGCA monthly average-fare series for back-testing "
                "(load via scripts/db/load_dgca_benchmark.py)",
            ],
            sources=[
                {
                    "id": s.id,
                    "name": s.name,
                    "kind": s.kind.value,
                    "channel": s.channel,
                    "enabled": s.enabled,
                    "tos_reviewed": s.tos_reviewed,
                    "rate_limit_rpm": s.rate_limit_rpm,
                    "crawl_delay_s": s.crawl_delay_s,
                    "fetch_mode": s.fetch_mode,
                    "is_synthetic": s.is_synthetic,
                    "notes": s.notes,
                }
                for s in self.reference.sources
            ],
        )
