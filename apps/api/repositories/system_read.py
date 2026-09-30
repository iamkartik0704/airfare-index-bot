"""Read queries for the system console: sources, health, freshness, jobs, sweeps."""

from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from packages.domain.enums import JobStatus, SweepStatus
from packages.domain.models.database import (
    IndexRun,
    IndexValueRow,
    NormalizedQuote,
    Route,
    ScrapeJob,
    Source,
    Sweep,
)


class SystemReadRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def ping(self) -> bool:
        self.session.execute(text("SELECT 1"))
        return True

    def sources(self) -> list[Source]:
        return list(self.session.scalars(select(Source).order_by(Source.kind, Source.id)))

    def newest_observation(self) -> tuple[datetime | None, date | None]:
        row = self.session.execute(
            select(
                func.max(NormalizedQuote.observed_at), func.max(NormalizedQuote.observation_date)
            ).where(NormalizedQuote.is_canonical.is_(True))
        ).one()
        return row[0], row[1]

    def latest_index(self) -> tuple[date | None, datetime | None]:
        latest_date = self.session.scalar(select(func.max(IndexValueRow.period_start)))
        run_at = self.session.scalar(select(func.max(IndexRun.completed_at)))
        return latest_date, run_at

    def queue_counts(self) -> dict[str, int]:
        rows = self.session.execute(
            select(ScrapeJob.status, func.count()).group_by(ScrapeJob.status)
        ).all()
        return {JobStatus(s).value: int(n) for s, n in rows}

    def jobs(
        self,
        *,
        status: JobStatus | None,
        source: str | None,
        sweep_id: uuid.UUID | None,
        limit: int,
        offset: int,
    ) -> tuple[list[tuple[ScrapeJob, str]], int]:
        stmt = select(ScrapeJob, Route.code).join(Route, Route.id == ScrapeJob.route_id)
        if status:
            stmt = stmt.where(ScrapeJob.status == status)
        if source:
            stmt = stmt.where(ScrapeJob.source_id == source)
        if sweep_id:
            stmt = stmt.where(ScrapeJob.sweep_id == sweep_id)
        total = int(self.session.scalar(select(func.count()).select_from(stmt.subquery())) or 0)
        rows = self.session.execute(
            stmt.order_by(ScrapeJob.updated_at.desc()).limit(limit).offset(offset)
        ).all()
        return [(j, c) for j, c in rows], total

    def job(self, job_id: uuid.UUID) -> tuple[ScrapeJob, str] | None:
        row = self.session.execute(
            select(ScrapeJob, Route.code)
            .join(Route, Route.id == ScrapeJob.route_id)
            .where(ScrapeJob.id == job_id)
        ).first()
        return None if row is None else (row[0], row[1])

    def sweeps(
        self, *, status: SweepStatus | None, limit: int, offset: int
    ) -> tuple[list[Sweep], int]:
        stmt = select(Sweep)
        if status:
            stmt = stmt.where(Sweep.status == status)
        total = int(self.session.scalar(select(func.count()).select_from(stmt.subquery())) or 0)
        rows = self.session.scalars(
            stmt.order_by(Sweep.created_at.desc()).limit(limit).offset(offset)
        )
        return list(rows), total

    def job_counts_for(self, sweep_ids: list[uuid.UUID]) -> dict[uuid.UUID, dict[str, int]]:
        out: dict[uuid.UUID, dict[str, int]] = {sid: {} for sid in sweep_ids}
        if not sweep_ids:
            return out
        rows = self.session.execute(
            select(ScrapeJob.sweep_id, ScrapeJob.status, func.count())
            .where(ScrapeJob.sweep_id.in_(sweep_ids))
            .group_by(ScrapeJob.sweep_id, ScrapeJob.status)
        ).all()
        for sid, status, n in rows:
            out[sid][JobStatus(status).value] = int(n)
        return out
