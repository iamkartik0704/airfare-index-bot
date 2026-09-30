"""The scrape-job queue (decision D1: ``scrape_jobs`` is the queue).

* **Idempotent enqueue** — one row per ``idempotency_key``
  (sweep slot × source × route × travel date × window); re-running the sweep
  generator for the same slot inserts nothing new.
* **Atomic claim** — ``UPDATE … WHERE id = :id AND status IN (PENDING, RETRY)``
  is a compare-and-set on every backend; two workers can never both win.
* **Per-source concurrency** — a job is only claimed while fewer than
  ``sources.max_concurrency`` jobs of that source hold a live lease (doc 10).
* **Leases** — a crashed worker's jobs are recovered once the lease expires.
* **Dead-letter** — terminal failures are ``FAILED`` and re-queued manually.
"""

from __future__ import annotations

import hashlib
import uuid
from collections import Counter
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Any

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from packages.domain.enums import JobStatus, SweepStatus, SweepTrigger
from packages.domain.models.database import ScrapeJob, Source, Sweep, utcnow
from packages.domain.repositories._upsert import upsert

CLAIMABLE = (JobStatus.PENDING, JobStatus.RETRY)


@dataclass(frozen=True)
class JobSpec:
    source_id: str
    route_id: int
    route_code: str
    travel_date: date
    purchase_window: int


def idempotency_key(slot: str, spec: JobSpec) -> str:
    raw = f"{slot}|{spec.source_id}|{spec.route_code}|{spec.travel_date}|{spec.purchase_window}"
    return hashlib.sha256(raw.encode()).hexdigest()


class JobRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    # ------------------------------------------------------------------ sweeps

    def get_or_create_sweep(
        self,
        *,
        slot: str,
        trigger: SweepTrigger,
        observation_date: date,
        parameters: dict[str, Any],
        requested_by: str,
    ) -> tuple[Sweep, bool]:
        existing = self.session.scalar(select(Sweep).where(Sweep.slot == slot))
        if existing is not None:
            return existing, False
        sweep = Sweep(
            slot=slot,
            trigger_type=trigger,
            observation_date=observation_date,
            parameters=parameters,
            requested_by=requested_by,
        )
        self.session.add(sweep)
        self.session.flush()
        return sweep, True

    def enqueue(self, sweep: Sweep, specs: Iterable[JobSpec], *, max_attempts: int) -> int:
        now = utcnow()
        rows = [
            {
                "id": uuid.uuid4(),
                "sweep_id": sweep.id,
                "source_id": s.source_id,
                "route_id": s.route_id,
                "observation_date": sweep.observation_date,
                "travel_date": s.travel_date,
                "purchase_window": s.purchase_window,
                "idempotency_key": idempotency_key(sweep.slot, s),
                "status": JobStatus.PENDING.value,
                "attempts": 0,
                "max_attempts": max_attempts,
                "available_at": now,
                "items_scraped": 0,
                "errors_encountered": 0,
                "created_at": now,
                "updated_at": now,
            }
            for s in specs
        ]
        before = self._count_for_sweep(sweep.id)
        for chunk_start in range(0, len(rows), 500):
            upsert(
                self.session,
                ScrapeJob.__table__,  # type: ignore[arg-type]
                rows[chunk_start : chunk_start + 500],
                conflict_columns=["idempotency_key"],
            )
        after = self._count_for_sweep(sweep.id)
        sweep.jobs_total = after
        self.session.flush()
        return after - before

    def _count_for_sweep(self, sweep_id: uuid.UUID) -> int:
        return int(
            self.session.scalar(
                select(func.count()).select_from(ScrapeJob).where(ScrapeJob.sweep_id == sweep_id)
            )
            or 0
        )

    def finalize_sweeps(self) -> int:
        """Mark RUNNING sweeps whose jobs are all terminal as completed."""
        finalized = 0
        for sweep in self.session.scalars(select(Sweep).where(Sweep.status == SweepStatus.RUNNING)):
            counts = self.status_counts(sweep_id=sweep.id)
            if any(counts.get(s, 0) for s in (*CLAIMABLE, JobStatus.RUNNING)):
                continue
            failed = counts.get(JobStatus.FAILED, 0) + counts.get(JobStatus.SKIPPED, 0)
            sweep.status = SweepStatus.COMPLETED_WITH_ERRORS if failed else SweepStatus.COMPLETED
            sweep.completed_at = utcnow()
            finalized += 1
        self.session.flush()
        return finalized

    # ------------------------------------------------------------------ claiming

    def claim(
        self, *, worker_id: str, limit: int, lease_seconds: int, now: datetime | None = None
    ) -> list[ScrapeJob]:
        now = now or utcnow()
        limits = dict(self.session.execute(select(Source.id, Source.max_concurrency)).all())
        running: Counter[str] = Counter(
            dict(
                self.session.execute(
                    select(ScrapeJob.source_id, func.count())
                    .where(ScrapeJob.status == JobStatus.RUNNING, ScrapeJob.lease_expires_at > now)
                    .group_by(ScrapeJob.source_id)
                ).all()
            )
        )
        candidates = self.session.execute(
            select(ScrapeJob.id, ScrapeJob.source_id)
            .where(ScrapeJob.status.in_(CLAIMABLE), ScrapeJob.available_at <= now)
            .order_by(ScrapeJob.available_at, ScrapeJob.created_at)
            .limit(limit * 10)
        ).all()
        claimed_ids: list[uuid.UUID] = []
        for job_id, source_id in candidates:
            if len(claimed_ids) >= limit:
                break
            if running[source_id] >= limits.get(source_id, 1):
                continue
            result = self.session.execute(
                update(ScrapeJob)
                .where(ScrapeJob.id == job_id, ScrapeJob.status.in_(CLAIMABLE))
                .values(
                    status=JobStatus.RUNNING,
                    attempts=ScrapeJob.attempts + 1,
                    worker_id=worker_id,
                    lease_expires_at=now + timedelta(seconds=lease_seconds),
                    started_at=now,
                    updated_at=now,
                )
            )
            if result.rowcount == 1:  # type: ignore[attr-defined]
                claimed_ids.append(job_id)
                running[source_id] += 1
        self.session.flush()
        if not claimed_ids:
            return []
        return list(self.session.scalars(select(ScrapeJob).where(ScrapeJob.id.in_(claimed_ids))))

    def recover_expired_leases(self, now: datetime | None = None) -> int:
        """Jobs whose worker died mid-flight go back to the queue (or dead-letter)."""
        now = now or utcnow()
        expired = list(
            self.session.scalars(
                select(ScrapeJob).where(
                    ScrapeJob.status == JobStatus.RUNNING, ScrapeJob.lease_expires_at < now
                )
            )
        )
        for job in expired:
            self._fail(
                job, code="lease_expired", message="worker lease expired", retry_in=0, now=now
            )
        self.session.flush()
        return len(expired)

    # ------------------------------------------------------------------ outcomes

    def mark_success(self, job: ScrapeJob, *, items: int, now: datetime | None = None) -> None:
        now = now or utcnow()
        job.status = JobStatus.SUCCESS
        job.items_scraped = items
        job.completed_at = now
        job.lease_expires_at = None
        job.last_error_code = None
        job.last_error_message = None

    def mark_failure(
        self,
        job: ScrapeJob,
        *,
        code: str,
        message: str,
        retryable: bool,
        retry_in: float,
        now: datetime | None = None,
    ) -> JobStatus:
        now = now or utcnow()
        if not retryable:
            job.attempts = max(job.attempts, job.max_attempts)
        return self._fail(job, code=code, message=message, retry_in=retry_in, now=now)

    def _fail(
        self, job: ScrapeJob, *, code: str, message: str, retry_in: float, now: datetime
    ) -> JobStatus:
        job.errors_encountered += 1
        job.last_error_code = code
        job.last_error_message = message[:2000]
        job.lease_expires_at = None
        if job.attempts < job.max_attempts:
            job.status = JobStatus.RETRY
            job.available_at = now + timedelta(seconds=retry_in)
        else:
            job.status = JobStatus.FAILED
            job.completed_at = now
        return job.status

    def mark_skipped(self, job: ScrapeJob, *, code: str, message: str) -> None:
        job.status = JobStatus.SKIPPED
        job.last_error_code = code
        job.last_error_message = message[:2000]
        job.completed_at = utcnow()
        job.lease_expires_at = None

    def requeue(self, job_ids: Sequence[uuid.UUID]) -> int:
        """Manual re-run (doc 10 DLQ): terminal jobs go back to PENDING with fresh attempts."""
        terminal = [s for s in JobStatus if s.is_terminal]
        now = utcnow()
        result = self.session.execute(
            update(ScrapeJob)
            .where(ScrapeJob.id.in_(list(job_ids)), ScrapeJob.status.in_(terminal))
            .values(
                status=JobStatus.PENDING,
                attempts=0,
                available_at=now,
                completed_at=None,
                updated_at=now,
            )
        )
        reopened = {
            sid
            for (sid,) in self.session.execute(
                select(ScrapeJob.sweep_id).where(ScrapeJob.id.in_(list(job_ids)))
            )
        }
        if reopened:
            self.session.execute(
                update(Sweep).where(Sweep.id.in_(reopened)).values(status=SweepStatus.RUNNING)
            )
        return int(result.rowcount)  # type: ignore[attr-defined]

    # ------------------------------------------------------------------ queries

    def get(self, job_id: uuid.UUID) -> ScrapeJob | None:
        return self.session.get(ScrapeJob, job_id)

    def status_counts(self, *, sweep_id: uuid.UUID | None = None) -> dict[JobStatus, int]:
        stmt = select(ScrapeJob.status, func.count()).group_by(ScrapeJob.status)
        if sweep_id is not None:
            stmt = stmt.where(ScrapeJob.sweep_id == sweep_id)
        return {JobStatus(status): int(n) for status, n in self.session.execute(stmt).all()}
