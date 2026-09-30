"""Sweep generation: fan out Routes × Sources × Purchase windows (doc 10).

A sweep is identified by its *slot* (``scheduled:2026-09-30T01:00+05:30``,
``manual:<uuid>``, ``backfill:2026-08-01``). Creating a sweep for a slot that
already exists enqueues nothing new — the scheduler can fire twice, or be
restarted mid-way, without duplicating work (doc 10 idempotency).

Back-filling past observation dates is only possible for the simulated
source: a real website cannot be scraped "as of" a past date.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import date, datetime, timedelta

from sqlalchemy.orm import Session

from packages.config.reference import ReferenceData, SourceDef
from packages.config.settings import Settings
from packages.domain.enums import SourceKind, SweepTrigger
from packages.domain.exceptions import ConfigurationError
from packages.domain.repositories.jobs import JobRepository, JobSpec
from packages.domain.repositories.reference import routes_by_code, sync_reference_data
from packages.observability.logging import get_logger
from packages.scraping.sources.registry import runnable_sources

log = get_logger("safar.sweep")


@dataclass(frozen=True)
class SweepResult:
    sweep_id: uuid.UUID
    slot: str
    created: bool
    jobs_enqueued: int
    jobs_total: int


class SweepGenerator:
    def __init__(self, settings: Settings, reference: ReferenceData) -> None:
        self._settings = settings
        self._reference = reference

    def _sources(self, only: list[str] | None, trigger: SweepTrigger) -> list[SourceDef]:
        if only:
            requested = [self._reference.source(s) for s in only]  # raises on unknown ids
            real = [s.id for s in requested if s.kind is not SourceKind.SIMULATED]
            if trigger is SweepTrigger.BACKFILL and real:
                raise ConfigurationError("only simulated sources can be back-filled", sources=real)
            runnable = {s.id for s in runnable_sources(self._reference, self._settings)}
            blocked = [s.id for s in requested if s.id not in runnable]
            if blocked:
                raise ConfigurationError(
                    "requested sources are disabled, not ToS-reviewed or have no adapter",
                    sources=blocked,
                )
            return requested
        sources = runnable_sources(self._reference, self._settings)
        if trigger is SweepTrigger.BACKFILL:
            sources = [s for s in sources if s.kind is SourceKind.SIMULATED]
        return sources

    def create(
        self,
        session: Session,
        *,
        observation_date: date,
        slot: str,
        trigger: SweepTrigger,
        requested_by: str = "scheduler",
        sources: list[str] | None = None,
        routes: list[str] | None = None,
        windows: tuple[int, ...] | None = None,
    ) -> SweepResult:
        sync_reference_data(session, self._reference)
        selected_sources = self._sources(sources, trigger)
        route_rows = routes_by_code(session)
        if routes:
            missing = set(routes) - set(route_rows)
            if missing:
                raise ConfigurationError("routes not in the active basket", routes=sorted(missing))
            route_rows = {code: r for code, r in route_rows.items() if code in routes}
        windows = windows or self._settings.scheduler.purchase_windows

        repo = JobRepository(session)
        sweep, created = repo.get_or_create_sweep(
            slot=slot,
            trigger=trigger,
            observation_date=observation_date,
            parameters={
                "sources": [s.id for s in selected_sources],
                "routes": sorted(route_rows),
                "windows": list(windows),
                "basket_version": self._reference.basket.version,
            },
            requested_by=requested_by,
        )
        specs = [
            JobSpec(
                source_id=source.id,
                route_id=route.id,
                route_code=code,
                travel_date=observation_date + timedelta(days=window),
                purchase_window=window,
            )
            for source in selected_sources
            for code, route in sorted(route_rows.items())
            for window in windows
        ]
        enqueued = repo.enqueue(sweep, specs, max_attempts=self._settings.worker.max_attempts)
        log.info(
            "sweep.created" if created else "sweep.reused",
            slot=slot,
            sweep_id=str(sweep.id),
            jobs_enqueued=enqueued,
            jobs_total=sweep.jobs_total,
        )
        return SweepResult(sweep.id, slot, created, enqueued, sweep.jobs_total)


def scheduled_slot(moment: datetime) -> str:
    return f"scheduled:{moment.replace(second=0, microsecond=0).isoformat()}"


def manual_slot() -> str:
    return f"manual:{uuid.uuid4()}"


def backfill_slot(observation_date: date) -> str:
    return f"backfill:{observation_date.isoformat()}"
