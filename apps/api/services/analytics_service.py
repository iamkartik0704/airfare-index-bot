"""Sector heatmap, carrier and channel analysis, cleaning funnel, fare explorer."""

from __future__ import annotations

from collections import defaultdict
from datetime import date
from decimal import Decimal

from sqlalchemy.orm import Session

from apps.api.repositories.fares_read import FareFilter, FaresReadRepository
from apps.api.repositories.index_read import IndexReadRepository
from apps.api.schemas.common import Page, data_origin
from apps.api.schemas.operations import (
    CarrierAnalysis,
    CarrierRow,
    ChannelAnalysis,
    ChannelRow,
    FareLineage,
    FareOut,
    FunnelOut,
    HeatCellOut,
    HeatmapOut,
)
from packages.config.settings import Settings
from packages.domain.enums import IndexFrequency, IndexScope
from packages.domain.exceptions import NotFoundError
from packages.domain.models.database import NormalizedQuote
from packages.index_engine.analytics import median_or_none, premium_pct, sector_heatmap


def fare_out(q: NormalizedQuote, route: str) -> FareOut:
    return FareOut(
        id=q.id,
        source_id=q.source_id,
        route=route,
        carrier_code=q.carrier_code,
        flight_number=q.flight_number,
        fare_class=q.fare_class,
        fare_family=q.fare_family,
        cabin=q.cabin,
        observation_date=q.observation_date,
        observed_at=q.observed_at,
        travel_date=q.travel_date,
        purchase_window=q.purchase_window,
        base_fare=q.base_fare,
        taxes=q.taxes,
        airport_fees=q.airport_fees,
        convenience_fee=q.convenience_fee,
        total_fare=q.total_fare,
        availability=q.availability,
        seats_left=q.seats_left,
        stops=q.stops,
        quality_flag=q.quality_flag,
        quality_reasons=list(q.quality_reasons),
        is_canonical=q.is_canonical,
        is_synthetic=q.is_synthetic,
    )


class AnalyticsService:
    def __init__(self, session: Session, settings: Settings) -> None:
        self.fares = FaresReadRepository(session)
        self.index = IndexReadRepository(session)
        self.settings = settings

    def _day(self, day: date | None) -> date:
        resolved = day or self.fares.latest_observation_date()
        if resolved is None:
            raise NotFoundError("no canonical quotes stored yet")
        return resolved

    def heatmap(self, frequency: IndexFrequency, periods: int) -> HeatmapOut:
        routes = {r.code: r.region for r in self.index.routes()}
        series: dict[str, list[tuple[str, Decimal]]] = {}
        all_periods: set[date] = set()
        synthetic: list[bool] = []
        for code in routes:
            rows = self.index.series(frequency, IndexScope.ROUTE, code)[-periods:]
            series[code] = [(r.period_start.isoformat(), r.value) for r in rows]
            all_periods.update(r.period_start for r in rows)
            synthetic.extend(r.is_synthetic for r in rows)
        cells = [
            HeatCellOut(
                route=c.route,
                region=routes[c.route],
                period=date.fromisoformat(c.period),
                value=c.value,
                change_pct=c.change_pct,
            )
            for c in sector_heatmap(series)
        ]
        return HeatmapOut(
            frequency=frequency.value,
            periods=sorted(all_periods),
            data_origin=data_origin(synthetic),
            cells=cells,
        )

    def carriers(self, day: date | None, route: str | None) -> CarrierAnalysis:
        day = self._day(day)
        rows = self.fares.index_eligible(day, route, list(self.settings.index.cabins))
        by_carrier: dict[str, list[Decimal]] = defaultdict(list)
        for _, carrier, _, total, _ in rows:
            by_carrier[carrier].append(total)
        overall = median_or_none([t for *_, t, _ in rows])
        names = self.fares.carrier_names()
        items = [
            CarrierRow(
                carrier_code=code,
                carrier_name=names.get(code, code),
                median_fare=median_or_none(totals) or Decimal(0),
                quote_count=len(totals),
                premium_pct=premium_pct(median_or_none(totals), overall),
            )
            for code, totals in sorted(by_carrier.items())
        ]
        return CarrierAnalysis(
            date=day, route=route, data_origin=data_origin(r[4] for r in rows), items=items
        )

    def channels(self, day: date | None) -> ChannelAnalysis:
        day = self._day(day)
        rows = self.fares.channel_pairs(day)
        groups: dict[tuple[str, str], dict[str, list[Decimal]]] = defaultdict(
            lambda: defaultdict(list)
        )
        for route, group, total, _, channel in rows:
            groups[(route, group)][channel].append(total)
        per_route: dict[str, dict[str, list[Decimal]]] = defaultdict(lambda: defaultdict(list))
        matched: dict[str, int] = defaultdict(int)
        for (route, _), channels in groups.items():
            if channels.get("direct") and channels.get("ota"):
                per_route[route]["direct"].extend(channels["direct"])
                per_route[route]["ota"].extend(channels["ota"])
                matched[route] += 1
        items = []
        for route in sorted(per_route):
            direct = median_or_none(per_route[route]["direct"])
            ota = median_or_none(per_route[route]["ota"])
            items.append(
                ChannelRow(
                    route=route,
                    direct_median=direct,
                    ota_median=ota,
                    wedge_pct=premium_pct(ota, direct),
                    matched_fares=matched[route],
                )
            )
        return ChannelAnalysis(date=day, data_origin=data_origin(r[3] for r in rows), items=items)

    def funnel(self, day: date | None, route: str | None) -> FunnelOut:
        day = self._day(day)
        return FunnelOut(observation_date=day, route=route, **self.fares.funnel(day, route))

    def fares_page(self, f: FareFilter, limit: int, offset: int) -> Page[FareOut]:
        rows, total = self.fares.page(f, limit=limit, offset=offset)
        return Page[FareOut](
            items=[fare_out(q, code) for q, code in rows], total=total, limit=limit, offset=offset
        )

    def fare_lineage(self, fare_id: int) -> FareLineage:
        found = self.fares.lineage(fare_id)
        if found is None:
            raise NotFoundError("fare not found", fare_id=fare_id)
        quote, route, raw, response, job = found
        return FareLineage(
            fare=fare_out(quote, route),
            raw_payload=raw.raw_payload,
            parser=f"{raw.parser_name}@{raw.parser_version}",
            response_id=response.id,
            response_url=response.request_url,
            response_status=response.status_code,
            response_sha256=response.sha256,
            fetched_at=response.fetched_at,
            job_id=job.id,
            sweep_id=job.sweep_id,
        )
