"""Read queries over the index store (API query side, decision D4)."""

from __future__ import annotations

from datetime import date

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from packages.domain.enums import IndexFrequency, IndexScope, RunStatus
from packages.domain.models.database import IndexObservationRow, IndexRun, IndexValueRow, Route


class IndexReadRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def series(
        self,
        frequency: IndexFrequency,
        scope: IndexScope,
        scope_key: str,
        start: date | None = None,
        end: date | None = None,
    ) -> list[IndexValueRow]:
        stmt = select(IndexValueRow).where(
            IndexValueRow.frequency == frequency,
            IndexValueRow.scope == scope,
            IndexValueRow.scope_key == scope_key,
        )
        if start:
            stmt = stmt.where(IndexValueRow.period_start >= start)
        if end:
            stmt = stmt.where(IndexValueRow.period_start <= end)
        return list(self.session.scalars(stmt.order_by(IndexValueRow.period_start)))

    def latest_period(self, frequency: IndexFrequency = IndexFrequency.DAILY) -> date | None:
        return self.session.scalar(
            select(func.max(IndexValueRow.period_start)).where(
                IndexValueRow.frequency == frequency, IndexValueRow.scope == IndexScope.HEADLINE
            )
        )

    def values_on(self, day: date, scopes: list[IndexScope]) -> list[IndexValueRow]:
        return list(
            self.session.scalars(
                select(IndexValueRow)
                .where(
                    IndexValueRow.frequency == IndexFrequency.DAILY,
                    IndexValueRow.period_start == day,
                    IndexValueRow.scope.in_(scopes),
                )
                .order_by(IndexValueRow.scope, IndexValueRow.scope_key)
            )
        )

    def value_on(self, day: date, scope: IndexScope, key: str = "") -> IndexValueRow | None:
        return self.session.scalar(
            select(IndexValueRow).where(
                IndexValueRow.frequency == IndexFrequency.DAILY,
                IndexValueRow.period_start == day,
                IndexValueRow.scope == scope,
                IndexValueRow.scope_key == key,
            )
        )

    def observations_on(self, day: date) -> list[tuple[IndexObservationRow, str]]:
        return [
            (obs, code)
            for obs, code in self.session.execute(
                select(IndexObservationRow, Route.code)
                .join(Route, Route.id == IndexObservationRow.route_id)
                .where(IndexObservationRow.observation_date == day)
                .order_by(Route.code, IndexObservationRow.purchase_window)
            ).all()
        ]

    def run(self, run_id: object) -> IndexRun | None:
        return self.session.get(IndexRun, run_id)

    def latest_run(self) -> IndexRun | None:
        return self.session.scalar(
            select(IndexRun)
            .where(IndexRun.status == RunStatus.SUCCESS)
            .order_by(IndexRun.started_at.desc())
            .limit(1)
        )

    def routes(self) -> list[Route]:
        return list(
            self.session.scalars(select(Route).where(Route.active.is_(True)).order_by(Route.code))
        )

    def route(self, code: str) -> Route | None:
        return self.session.scalar(select(Route).where(Route.code == code))
