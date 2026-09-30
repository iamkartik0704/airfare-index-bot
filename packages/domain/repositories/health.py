"""Source health: hourly counters and the persisted source status / circuit."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from packages.domain.enums import SourceStatus
from packages.domain.models.database import Source, SourceHealth, utcnow
from packages.domain.repositories._upsert import upsert

COUNTER_FIELDS = (
    "requests",
    "jobs_succeeded",
    "jobs_failed",
    "blocked",
    "rate_limited",
    "parse_errors",
    "robots_denied",
    "quotes_collected",
    "missing_fields",
    "total_latency_ms",
)


@dataclass
class HealthDelta:
    requests: int = 0
    jobs_succeeded: int = 0
    jobs_failed: int = 0
    blocked: int = 0
    rate_limited: int = 0
    parse_errors: int = 0
    robots_denied: int = 0
    quotes_collected: int = 0
    missing_fields: int = 0
    total_latency_ms: int = 0
    status_codes: dict[str, int] = field(default_factory=dict)


def hour_bucket(moment: datetime) -> datetime:
    return moment.replace(minute=0, second=0, microsecond=0)


class SourceHealthRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def record(self, source_id: str, delta: HealthDelta, *, at: datetime | None = None) -> None:
        """Atomically add ``delta`` to the source's current hourly bucket."""
        bucket = hour_bucket(at or utcnow())
        upsert(
            self.session,
            SourceHealth.__table__,  # type: ignore[arg-type]
            [
                {
                    "source_id": source_id,
                    "bucket_start": bucket,
                    "status_codes": {},
                    **dict.fromkeys(COUNTER_FIELDS, 0),
                }
            ],
            conflict_columns=["source_id", "bucket_start"],
        )
        increments = {f: getattr(SourceHealth, f) + getattr(delta, f) for f in COUNTER_FIELDS}
        self.session.execute(
            update(SourceHealth)
            .where(SourceHealth.source_id == source_id, SourceHealth.bucket_start == bucket)
            .values(**increments)
        )
        if delta.status_codes:
            row = self.session.scalar(
                select(SourceHealth).where(
                    SourceHealth.source_id == source_id, SourceHealth.bucket_start == bucket
                )
            )
            if row is not None:
                codes = dict(row.status_codes)
                for code, n in delta.status_codes.items():
                    codes[code] = codes.get(code, 0) + n
                row.status_codes = codes
        self.session.flush()

    def window(self, since: datetime) -> dict[str, dict[str, int]]:
        """Summed counters per source since ``since``."""
        columns = [func.coalesce(func.sum(getattr(SourceHealth, f)), 0) for f in COUNTER_FIELDS]
        stmt = (
            select(SourceHealth.source_id, *columns)
            .where(SourceHealth.bucket_start >= hour_bucket(since))
            .group_by(SourceHealth.source_id)
        )
        return {
            row[0]: dict(zip(COUNTER_FIELDS, (int(v) for v in row[1:]), strict=True))
            for row in self.session.execute(stmt).all()
        }

    # ------------------------------------------------------------------ status

    def get_source(self, source_id: str) -> Source | None:
        return self.session.get(Source, source_id)

    def set_status(
        self,
        source: Source,
        status: SourceStatus,
        *,
        reason: str | None,
        open_until: datetime | None = None,
    ) -> None:
        if source.status is not status:
            source.status_changed_at = utcnow()
        source.status = status
        source.status_reason = reason
        if open_until is not None:
            source.circuit_open_until = open_until
        self.session.flush()

    def record_circuit(
        self, source: Source, *, consecutive_failures: int, open_until: datetime | None
    ) -> None:
        source.consecutive_failures = consecutive_failures
        source.circuit_open_until = open_until
        self.session.flush()

    def recent_buckets(self, source_id: str, hours: int) -> list[SourceHealth]:
        since = hour_bucket(utcnow() - timedelta(hours=hours))
        return list(
            self.session.scalars(
                select(SourceHealth)
                .where(SourceHealth.source_id == source_id, SourceHealth.bucket_start >= since)
                .order_by(SourceHealth.bucket_start)
            )
        )
