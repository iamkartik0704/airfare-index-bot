"""Index store: canonical cell extraction, runs, observations and values."""

from __future__ import annotations

import uuid
from collections import defaultdict
from collections.abc import Sequence
from datetime import date
from decimal import Decimal
from typing import Any

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from packages.domain.enums import AvailabilityStatus, QualityFlag, RunStatus
from packages.domain.models.database import (
    IndexObservationRow,
    IndexRun,
    IndexValueRow,
    NormalizedQuote,
    Route,
    utcnow,
)
from packages.domain.models.index import IndexObservation, IndexValue, PriceCell
from packages.domain.repositories._upsert import upsert


class IndexRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def observation_date_bounds(self) -> tuple[date | None, date | None]:
        row = self.session.execute(
            select(
                func.min(NormalizedQuote.observation_date),
                func.max(NormalizedQuote.observation_date),
            ).where(NormalizedQuote.is_canonical.is_(True))
        ).one()
        return row[0], row[1]

    def canonical_cells(
        self,
        date_from: date,
        date_to: date,
        *,
        cabins: Sequence[str],
        include_connecting: bool,
    ) -> list[PriceCell]:
        """Index-eligible fares: canonical, VALID, AVAILABLE, in-basket cabin (doc 09 input)."""
        stmt = (
            select(
                NormalizedQuote.observation_date,
                Route.code,
                NormalizedQuote.purchase_window,
                NormalizedQuote.total_fare,
                NormalizedQuote.quality_factor,
                NormalizedQuote.source_id,
                NormalizedQuote.is_synthetic,
            )
            .join(Route, Route.id == NormalizedQuote.route_id)
            .where(
                NormalizedQuote.observation_date.between(date_from, date_to),
                NormalizedQuote.is_canonical.is_(True),
                NormalizedQuote.quality_flag == QualityFlag.VALID,
                NormalizedQuote.availability == AvailabilityStatus.AVAILABLE,
                NormalizedQuote.cabin.in_(list(cabins)),
                NormalizedQuote.total_fare.is_not(None),
            )
        )
        if not include_connecting:
            stmt = stmt.where(or_(NormalizedQuote.stops.is_(None), NormalizedQuote.stops == 0))
        grouped: dict[tuple[date, str, int], list[tuple[Decimal, Decimal, str, bool]]] = (
            defaultdict(list)
        )
        for obs_date, code, window, total, quality, source, synthetic in self.session.execute(stmt):
            if total is None:
                continue
            grouped[(obs_date, code, window)].append((total, quality, source, synthetic))
        return [
            PriceCell(
                observation_date=k[0],
                route_code=k[1],
                purchase_window=k[2],
                fares=tuple(v[0] for v in rows),
                quality_factors=tuple(v[1] for v in rows),
                source_count=len({v[2] for v in rows}),
                is_synthetic=any(v[3] for v in rows),
            )
            for k, rows in sorted(grouped.items())
        ]

    # ------------------------------------------------------------------ runs

    def start_run(self, date_from: date, date_to: date) -> IndexRun:
        run = IndexRun(status=RunStatus.RUNNING, date_from=date_from, date_to=date_to)
        self.session.add(run)
        self.session.flush()
        return run

    def finish_run(
        self,
        run: IndexRun,
        *,
        status: RunStatus,
        parameters: dict[str, Any] | None = None,
        base_period: tuple[date, date] | None = None,
        error: str | None = None,
    ) -> None:
        run.status = status
        run.completed_at = utcnow()
        if parameters is not None:
            run.parameters = parameters
        if base_period is not None:
            run.base_period_start, run.base_period_end = base_period
        run.error_message = error
        self.session.flush()

    def latest_run(self, status: RunStatus | None = RunStatus.SUCCESS) -> IndexRun | None:
        stmt = select(IndexRun).order_by(IndexRun.started_at.desc()).limit(1)
        if status is not None:
            stmt = stmt.where(IndexRun.status == status)
        return self.session.scalar(stmt)

    # ------------------------------------------------------------------ results

    def upsert_observations(
        self, run_id: uuid.UUID, observations: Sequence[IndexObservation], route_ids: dict[str, int]
    ) -> None:
        rows = [
            {
                "index_run_id": run_id,
                "observation_date": o.observation_date,
                "route_id": route_ids[o.route_code],
                "purchase_window": o.purchase_window,
                "median_fare": o.median_fare,
                "mean_fare": o.mean_fare,
                "min_fare": o.min_fare,
                "max_fare": o.max_fare,
                "quote_count": o.quote_count,
                "source_count": o.source_count,
                "quality_factor": o.quality_factor,
                "imputed": o.imputed,
                "imputation_method": o.imputation_method.value,
                "imputed_from_date": o.imputed_from_date,
                "is_synthetic": o.is_synthetic,
            }
            for o in observations
            if o.route_code in route_ids
        ]
        cols = (
            [c for c in rows[0] if c not in ("observation_date", "route_id", "purchase_window")]
            if rows
            else []
        )
        for start in range(0, len(rows), 500):
            upsert(
                self.session,
                IndexObservationRow.__table__,  # type: ignore[arg-type]
                rows[start : start + 500],
                conflict_columns=["observation_date", "route_id", "purchase_window"],
                update_columns=cols,
            )

    def upsert_values(self, run_id: uuid.UUID, values: Sequence[IndexValue]) -> None:
        rows = [
            {
                "index_run_id": run_id,
                "frequency": v.frequency.value,
                "scope": v.scope.value,
                "scope_key": v.scope_key,
                "period_start": v.period_start,
                "period_end": v.period_end,
                "value": v.value,
                "nominal_value": v.nominal_value,
                "avg_fare": v.avg_fare,
                "observation_count": v.observation_count,
                "coverage_pct": v.coverage_pct,
                "imputed_share": v.imputed_share,
                "is_synthetic": v.is_synthetic,
            }
            for v in values
        ]
        update_cols = [
            "index_run_id",
            "period_end",
            "value",
            "nominal_value",
            "avg_fare",
            "observation_count",
            "coverage_pct",
            "imputed_share",
            "is_synthetic",
        ]
        for start in range(0, len(rows), 500):
            upsert(
                self.session,
                IndexValueRow.__table__,  # type: ignore[arg-type]
                rows[start : start + 500],
                conflict_columns=["frequency", "scope", "scope_key", "period_start"],
                update_columns=update_cols,
            )
