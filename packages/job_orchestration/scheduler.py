"""Cron triggering with APScheduler (docs 10, 16 target A).

* ``sweep``        — ``scheduler.sweep_cron`` (default 01:00 IST): fan out jobs.
* ``index``        — ``scheduler.index_cron`` (default 06:30 IST): recompute APIx.
* ``housekeeping`` — every 5 minutes: recover expired leases, finalise sweeps,
  refresh freshness/queue gauges.

Every sweep slot is derived from the cron fire time, so a double fire or a
restart can never enqueue a sweep twice. On start-up the scheduler *catches
up*: if the most recent sweep fire time was missed while it was down, that
slot is created immediately (idempotently).
"""

from __future__ import annotations

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy import func, select

from packages.config.reference import ReferenceData
from packages.config.settings import Settings
from packages.domain.db import session_scope
from packages.domain.enums import SweepTrigger
from packages.domain.exceptions import SafarError
from packages.domain.models.database import NormalizedQuote, utcnow
from packages.domain.repositories.jobs import JobRepository
from packages.index_engine.service import IndexService
from packages.job_orchestration.sweep import SweepGenerator
from packages.observability.logging import get_logger
from packages.observability.metrics import metrics

log = get_logger("safar.scheduler")


def last_fire_time(trigger: CronTrigger, now: datetime) -> datetime | None:
    """Most recent fire time ≤ ``now`` within the past two days."""
    candidate = trigger.get_next_fire_time(None, now - timedelta(days=2))
    last = None
    while candidate is not None and candidate <= now:
        last = candidate
        candidate = trigger.get_next_fire_time(candidate, candidate + timedelta(seconds=1))
    return last


class Scheduler:
    def __init__(self, settings: Settings, reference: ReferenceData) -> None:
        self._settings = settings
        self._reference = reference
        self._tz = ZoneInfo(settings.scheduler.timezone)
        self._sweep_trigger = CronTrigger.from_crontab(
            settings.scheduler.sweep_cron, timezone=self._tz
        )
        self._index_trigger = CronTrigger.from_crontab(
            settings.scheduler.index_cron, timezone=self._tz
        )

    def run_sweep(self, fire_time: datetime | None = None) -> None:
        # The slot is the *scheduled* fire time (not wall-clock), so a late or
        # repeated execution of the same cron tick maps to the same sweep.
        now = datetime.now(self._tz)
        fire = (fire_time or last_fire_time(self._sweep_trigger, now) or now).astimezone(self._tz)
        fire = fire.replace(second=0, microsecond=0)
        try:
            with session_scope() as session:
                SweepGenerator(self._settings, self._reference).create(
                    session,
                    observation_date=fire.date(),
                    slot=f"scheduled:{fire.isoformat()}",
                    trigger=SweepTrigger.SCHEDULED,
                )
        except SafarError as exc:
            log.error("scheduler.sweep_failed", error_code=exc.code, error=str(exc))

    def run_index(self) -> None:
        try:
            with session_scope() as session:
                IndexService(self._settings, self._reference).compute(session)
        except SafarError as exc:
            log.error("scheduler.index_failed", error_code=exc.code, error=str(exc))

    def housekeeping(self) -> None:
        try:
            with session_scope() as session:
                repo = JobRepository(session)
                recovered = repo.recover_expired_leases()
                repo.finalize_sweeps()
                for status, n in repo.status_counts().items():
                    metrics.QUEUE_DEPTH.labels(status.value).set(n)
                newest = session.scalar(
                    select(func.max(NormalizedQuote.observed_at)).where(
                        NormalizedQuote.is_canonical.is_(True)
                    )
                )
                if newest is not None:
                    metrics.DATA_FRESHNESS.set((utcnow() - newest).total_seconds())
                if recovered:
                    log.warning("scheduler.leases_recovered", count=recovered)
        except SafarError as exc:
            log.error("scheduler.housekeeping_failed", error_code=exc.code, error=str(exc))

    def catch_up(self) -> None:
        missed = last_fire_time(self._sweep_trigger, datetime.now(self._tz))
        if missed is not None:
            log.info("scheduler.catch_up", slot_time=missed.isoformat())
            self.run_sweep(missed)

    def start(self) -> None:
        scheduler = BlockingScheduler(timezone=self._tz)
        common = {"coalesce": True, "max_instances": 1, "misfire_grace_time": 3600}
        scheduler.add_job(self.run_sweep, self._sweep_trigger, id="sweep", **common)
        scheduler.add_job(self.run_index, self._index_trigger, id="index", **common)
        scheduler.add_job(self.housekeeping, "interval", minutes=5, id="housekeeping", **common)
        self.catch_up()
        self.housekeeping()
        log.info(
            "scheduler.started",
            sweep_cron=self._settings.scheduler.sweep_cron,
            index_cron=self._settings.scheduler.index_cron,
            timezone=self._settings.scheduler.timezone,
        )
        scheduler.start()
