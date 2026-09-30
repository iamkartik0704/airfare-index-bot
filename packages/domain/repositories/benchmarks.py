"""DGCA benchmark rows and back-test results."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from packages.domain.enums import IndexFrequency, IndexScope, RunStatus
from packages.domain.models.database import (
    BacktestPoint,
    BacktestRun,
    DgcaBenchmark,
    IndexValueRow,
    utcnow,
)
from packages.domain.repositories._upsert import upsert


@dataclass(frozen=True)
class BenchmarkRecord:
    period_month: date
    route_code: str
    avg_fare: Decimal
    source_label: str
    source_url: str | None
    is_synthetic: bool


class BenchmarkRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def upsert(self, records: Sequence[BenchmarkRecord]) -> int:
        upsert(
            self.session,
            DgcaBenchmark.__table__,  # type: ignore[arg-type]
            [
                {
                    "period_month": r.period_month.replace(day=1),
                    "route_code": r.route_code,
                    "avg_fare": r.avg_fare,
                    "source_label": r.source_label,
                    "source_url": r.source_url,
                    "is_synthetic": r.is_synthetic,
                    "loaded_at": utcnow(),
                }
                for r in records
            ],
            conflict_columns=["period_month", "route_code"],
            update_columns=["avg_fare", "source_label", "source_url", "is_synthetic", "loaded_at"],
        )
        return len(records)

    def monthly(self, route_code: str = "ALL") -> list[DgcaBenchmark]:
        return list(
            self.session.scalars(
                select(DgcaBenchmark)
                .where(DgcaBenchmark.route_code == route_code)
                .order_by(DgcaBenchmark.period_month)
            )
        )

    def daily_headline(self, date_from: date, date_to: date) -> list[IndexValueRow]:
        return list(
            self.session.scalars(
                select(IndexValueRow)
                .where(
                    IndexValueRow.frequency == IndexFrequency.DAILY,
                    IndexValueRow.scope == IndexScope.HEADLINE,
                    IndexValueRow.period_start.between(date_from, date_to),
                )
                .order_by(IndexValueRow.period_start)
            )
        )

    def save_run(
        self,
        *,
        period: tuple[date, date],
        days_covered: int,
        benchmark_label: str,
        benchmark_is_synthetic: bool,
        apix_is_synthetic: bool,
        metrics: dict[str, Any],
        verdict: str,
        points: Sequence[dict[str, Any]],
    ) -> BacktestRun:
        run = BacktestRun(
            status=RunStatus.SUCCESS,
            period_start=period[0],
            period_end=period[1],
            days_covered=days_covered,
            benchmark_label=benchmark_label,
            benchmark_is_synthetic=benchmark_is_synthetic,
            apix_is_synthetic=apix_is_synthetic,
            metrics=metrics,
            verdict=verdict,
        )
        run.points = [BacktestPoint(**p) for p in points]
        self.session.add(run)
        self.session.flush()
        return run

    def latest_run(self) -> BacktestRun | None:
        return self.session.scalar(
            select(BacktestRun).order_by(BacktestRun.created_at.desc()).limit(1)
        )
