"""Index, route and lead-time read services."""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy.orm import Session

from apps.api.repositories.index_read import IndexReadRepository
from apps.api.schemas.common import data_origin
from apps.api.schemas.index import (
    Headline,
    IndexPoint,
    IndexSeries,
    LeadTimeOut,
    LeadTimePointOut,
    Lineage,
    LineageCell,
    RouteSummary,
    RouteTrends,
    SubIndex,
    SubIndices,
)
from packages.config.reference import ReferenceData
from packages.config.settings import Settings
from packages.domain.enums import IndexFrequency, IndexScope
from packages.domain.exceptions import NotFoundError
from packages.domain.models.database import IndexValueRow
from packages.index_engine.aggregation.periods import rolling_mean
from packages.index_engine.analytics import lead_time_curve, premium_pct, weighted_window_fares

HUNDRED = Decimal(100)


def _pct_change(now: Decimal | None, before: Decimal | None) -> Decimal | None:
    return premium_pct(now, before)


def _point(row: IndexValueRow, rolling: Decimal | None = None) -> IndexPoint:
    return IndexPoint(
        period_start=row.period_start,
        period_end=row.period_end,
        value=row.value,
        nominal_value=row.nominal_value,
        rolling_value=rolling.quantize(Decimal("0.0001")) if rolling is not None else None,
        avg_fare=row.avg_fare,
        observation_count=row.observation_count,
        coverage_pct=row.coverage_pct,
        imputed_share=row.imputed_share,
        is_synthetic=row.is_synthetic,
    )


class IndexQueryService:
    def __init__(self, session: Session, settings: Settings, reference: ReferenceData) -> None:
        self.repo = IndexReadRepository(session)
        self.settings = settings
        self.reference = reference

    def _base_period(self) -> tuple[date, date] | None:
        run = self.repo.latest_run()
        if run and run.base_period_start and run.base_period_end:
            return run.base_period_start, run.base_period_end
        return None

    def series(
        self,
        frequency: IndexFrequency,
        scope: IndexScope = IndexScope.HEADLINE,
        scope_key: str = "",
        start: date | None = None,
        end: date | None = None,
    ) -> IndexSeries:
        rows = self.repo.series(frequency, scope, scope_key, start, end)
        if frequency is IndexFrequency.DAILY:
            rolled = (
                rolling_mean([r.value for r in rows], self.settings.index.rolling_days)
                if rows
                else []
            )
            points = [_point(r, rv) for r, rv in zip(rows, rolled, strict=True)]
        else:
            points = [_point(r) for r in rows]
        return IndexSeries(
            frequency=frequency,
            scope=scope,
            scope_key=scope_key,
            data_origin=data_origin(r.is_synthetic for r in rows),
            base_period=self._base_period(),
            items=points,
        )

    def headline(self) -> Headline:
        latest = self.repo.latest_period()
        if latest is None:
            raise NotFoundError("no index has been computed yet")
        window = self.repo.series(
            IndexFrequency.DAILY, IndexScope.HEADLINE, "", latest - timedelta(days=45), latest
        )
        by_day = {r.period_start: r for r in window}
        today = by_day[latest]
        monthly = self.repo.series(IndexFrequency.MONTHLY, IndexScope.HEADLINE, "")
        mom = _pct_change(monthly[-1].value, monthly[-2].value) if len(monthly) >= 2 else None
        recent = [r.value for r in window[-self.settings.index.rolling_days :]]
        run = self.repo.latest_run()
        return Headline(
            date=latest,
            value=today.value,
            nominal_value=today.nominal_value,
            rolling_value=(sum(recent, Decimal(0)) / len(recent)).quantize(Decimal("0.0001")),
            avg_fare=today.avg_fare,
            change_dod_pct=_pct_change(
                today.value, getattr(by_day.get(latest - timedelta(days=1)), "value", None)
            ),
            change_wow_pct=_pct_change(
                today.value, getattr(by_day.get(latest - timedelta(days=7)), "value", None)
            ),
            change_mom_pct=mom,
            coverage_pct=today.coverage_pct,
            imputed_share=today.imputed_share,
            observation_count=today.observation_count,
            base_period=self._base_period(),
            computed_at=run.completed_at if run else None,
            data_origin=data_origin([today.is_synthetic]),
            methodology_status={
                "basket_weights": self.reference.basket.status,
                "hedonic_factors": self.reference.fare_classes.status,
                "hedonic_adjustment": "ON" if self.settings.index.hedonic_adjustment else "OFF",
            },
        )

    def sub_indices(self, day: date | None) -> SubIndices:
        day = day or self.repo.latest_period()
        if day is None:
            raise NotFoundError("no index has been computed yet")
        rows = self.repo.values_on(day, [IndexScope.WINDOW, IndexScope.REGION])
        if not rows:
            raise NotFoundError("no sub-indices for date", date=day.isoformat())
        previous = {
            (r.scope, r.scope_key): r.value
            for r in self.repo.values_on(
                day - timedelta(days=7), [IndexScope.WINDOW, IndexScope.REGION]
            )
        }
        items = [
            SubIndex(
                scope=r.scope,
                scope_key=r.scope_key,
                value=r.value,
                change_pct=_pct_change(r.value, previous.get((r.scope, r.scope_key))),
                avg_fare=r.avg_fare,
            )
            for r in sorted(rows, key=lambda r: (r.scope.value, _window_order(r.scope_key)))
        ]
        return SubIndices(
            date=day, data_origin=data_origin(r.is_synthetic for r in rows), items=items
        )

    def lineage(self, day: date) -> Lineage:
        headline = self.repo.value_on(day, IndexScope.HEADLINE)
        if headline is None:
            raise NotFoundError("no index value for date", date=day.isoformat())
        run = self.repo.run(headline.index_run_id)
        cells = [
            LineageCell(
                route=code,
                purchase_window=obs.purchase_window,
                median_fare=obs.median_fare,
                quote_count=obs.quote_count,
                source_count=obs.source_count,
                imputed=obs.imputed,
                imputed_from_date=obs.imputed_from_date,
                is_synthetic=obs.is_synthetic,
            )
            for obs, code in self.repo.observations_on(day)
        ]
        return Lineage(
            date=day,
            index_value=headline.value,
            index_run_id=str(headline.index_run_id),
            computed_at=run.completed_at if run else None,
            parameters=run.parameters if run else {},
            cells=cells,
            quotes_endpoint=f"/api/v1/fares?observation_date={day.isoformat()}&canonical_only=true",
        )

    # ------------------------------------------------------------------ routes

    def _route_summary(self, code: str, latest: date | None) -> RouteSummary:
        route = self.repo.route(code)
        if route is None:
            raise NotFoundError("route not in basket", route=code)
        weights = self.reference.basket.normalized_weights()
        value = self.repo.value_on(latest, IndexScope.ROUTE, code) if latest else None
        monthly = self.repo.series(IndexFrequency.MONTHLY, IndexScope.ROUTE, code)
        return RouteSummary(
            code=route.code,
            origin=route.origin_iata,
            destination=route.destination_iata,
            distance_km=route.distance_km,
            region=route.region,
            weight=route.dgca_weight,
            weight_share_pct=(HUNDRED * weights.get(code, Decimal(0))).quantize(Decimal("0.01")),
            latest_index=value.value if value else None,
            latest_avg_fare=value.avg_fare if value else None,
            change_mom_pct=_pct_change(monthly[-1].value, monthly[-2].value)
            if len(monthly) >= 2
            else None,
        )

    def routes(self) -> list[RouteSummary]:
        latest = self.repo.latest_period()
        return [self._route_summary(r.code, latest) for r in self.repo.routes()]

    def lead_time(self, day: date | None, route: str | None = None) -> LeadTimeOut:
        day = day or self.repo.latest_period()
        if day is None:
            raise NotFoundError("no index has been computed yet")
        observations = self.repo.observations_on(day)
        if route:
            observations = [(o, c) for o, c in observations if c == route]
        if not observations:
            raise NotFoundError("no observations for date", date=day.isoformat(), route=route or "")
        medians = {(code, o.purchase_window): o.median_fare for o, code in observations}
        if route:
            fares = {w: f for (_, w), f in medians.items()}
        else:
            fares = weighted_window_fares(medians, self.reference.basket.normalized_weights())
        curve = lead_time_curve(fares)
        return LeadTimeOut(
            date=day,
            route=route,
            elasticity=curve.elasticity,
            cheapest_window=curve.cheapest_window,
            data_origin=data_origin(o.is_synthetic for o, _ in observations),
            points=[LeadTimePointOut(**p.__dict__) for p in curve.points],
        )

    def route_trends(self, code: str, start: date | None, end: date | None) -> RouteTrends:
        latest = self.repo.latest_period()
        summary = self._route_summary(code, latest)
        history = self.series(IndexFrequency.DAILY, IndexScope.ROUTE, code, start, end)
        return RouteTrends(
            route=summary,
            lead_time=self.lead_time(latest, code),
            history=history.items,
            data_origin=history.data_origin,
        )


def _window_order(key: str) -> int:
    return int(key[2:]) if key.startswith("T+") and key[2:].isdigit() else 999
