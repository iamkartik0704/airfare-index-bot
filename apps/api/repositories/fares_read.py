"""Read queries over canonical and raw quotes."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from sqlalchemy import Select, case, func, select
from sqlalchemy.orm import Session

from packages.domain.enums import AvailabilityStatus, QualityFlag
from packages.domain.models.database import (
    Carrier,
    NormalizedQuote,
    RawQuote,
    RawResponse,
    Route,
    ScrapeJob,
    Source,
)


@dataclass(frozen=True)
class FareFilter:
    route: str | None = None
    observation_date: date | None = None
    travel_date: date | None = None
    purchase_window: int | None = None
    carrier: str | None = None
    source: str | None = None
    quality_flag: QualityFlag | None = None
    canonical_only: bool = False


class FaresReadRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def _filtered(self, f: FareFilter) -> Select[NormalizedQuote, str]:
        stmt = select(NormalizedQuote, Route.code).join(Route, Route.id == NormalizedQuote.route_id)
        if f.route:
            stmt = stmt.where(Route.code == f.route)
        if f.observation_date:
            stmt = stmt.where(NormalizedQuote.observation_date == f.observation_date)
        if f.travel_date:
            stmt = stmt.where(NormalizedQuote.travel_date == f.travel_date)
        if f.purchase_window is not None:
            stmt = stmt.where(NormalizedQuote.purchase_window == f.purchase_window)
        if f.carrier:
            stmt = stmt.where(NormalizedQuote.carrier_code == f.carrier)
        if f.source:
            stmt = stmt.where(NormalizedQuote.source_id == f.source)
        if f.quality_flag:
            stmt = stmt.where(NormalizedQuote.quality_flag == f.quality_flag)
        if f.canonical_only:
            stmt = stmt.where(NormalizedQuote.is_canonical.is_(True))
        return stmt

    def page(
        self, f: FareFilter, *, limit: int, offset: int
    ) -> tuple[list[tuple[NormalizedQuote, str]], int]:
        stmt = self._filtered(f)
        total = int(self.session.scalar(select(func.count()).select_from(stmt.subquery())) or 0)
        rows = self.session.execute(
            stmt.order_by(NormalizedQuote.observed_at.desc(), NormalizedQuote.id.desc())
            .limit(limit)
            .offset(offset)
        ).all()
        return [(row[0], row[1]) for row in rows], total

    def lineage(
        self, fare_id: int
    ) -> tuple[NormalizedQuote, str, RawQuote, RawResponse, ScrapeJob] | None:
        row = self.session.execute(
            select(NormalizedQuote, Route.code, RawQuote, RawResponse, ScrapeJob)
            .join(Route, Route.id == NormalizedQuote.route_id)
            .join(RawQuote, RawQuote.id == NormalizedQuote.raw_quote_id)
            .join(RawResponse, RawResponse.id == RawQuote.response_id)
            .join(ScrapeJob, ScrapeJob.id == NormalizedQuote.job_id)
            .where(NormalizedQuote.id == fare_id)
        ).first()
        return None if row is None else (row[0], row[1], row[2], row[3], row[4])

    def funnel(self, day: date, route: str | None) -> dict[str, int]:
        nq = NormalizedQuote
        stmt = (
            select(
                func.count(),
                func.sum(case((nq.quality_flag == QualityFlag.VALID, 1), else_=0)),
                func.sum(case((nq.quality_flag == QualityFlag.OUTLIER, 1), else_=0)),
                func.sum(case((nq.quality_flag == QualityFlag.DUPLICATE, 1), else_=0)),
                func.sum(case((nq.quality_flag == QualityFlag.INVALID, 1), else_=0)),
                func.sum(case((nq.availability == AvailabilityStatus.SOLD_OUT, 1), else_=0)),
                func.sum(case((nq.availability == AvailabilityStatus.CANCELLED, 1), else_=0)),
                func.sum(case((nq.is_canonical.is_(True), 1), else_=0)),
            )
            .join(Route, Route.id == nq.route_id)
            .where(nq.observation_date == day)
        )
        raw_stmt = (
            select(func.count())
            .select_from(RawQuote)
            .join(Route, Route.id == RawQuote.route_id)
            .where(RawQuote.observation_date == day)
        )
        if route:
            stmt = stmt.where(Route.code == route)
            raw_stmt = raw_stmt.where(Route.code == route)
        row = self.session.execute(stmt).one()
        keys = (
            "normalized",
            "valid",
            "outliers",
            "duplicates",
            "invalid",
            "sold_out",
            "cancelled",
            "canonical",
        )
        counts = {k: int(v or 0) for k, v in zip(keys, row, strict=True)}
        counts["raw"] = int(self.session.scalar(raw_stmt) or 0)
        return counts

    def index_eligible(
        self, day: date, route: str | None, cabins: list[str]
    ) -> list[tuple[str, str, int, Decimal, bool]]:
        """(route, carrier, window, total, synthetic) of canonical valid available fares."""
        stmt = (
            select(
                Route.code,
                NormalizedQuote.carrier_code,
                NormalizedQuote.purchase_window,
                NormalizedQuote.total_fare,
                NormalizedQuote.is_synthetic,
            )
            .join(Route, Route.id == NormalizedQuote.route_id)
            .where(
                NormalizedQuote.observation_date == day,
                NormalizedQuote.is_canonical.is_(True),
                NormalizedQuote.quality_flag == QualityFlag.VALID,
                NormalizedQuote.availability == AvailabilityStatus.AVAILABLE,
                NormalizedQuote.cabin.in_(cabins),
            )
        )
        if route:
            stmt = stmt.where(Route.code == route)
        return [
            (r, c, w, t, s) for r, c, w, t, s in self.session.execute(stmt).all() if t is not None
        ]

    def channel_pairs(self, day: date) -> list[tuple[str, str, Decimal, bool, str]]:
        """(route, group_key, total, synthetic, channel) for live valid priced fares on ``day``."""
        stmt = (
            select(
                Route.code,
                NormalizedQuote.group_key,
                NormalizedQuote.total_fare,
                NormalizedQuote.is_synthetic,
                Source.channel,
            )
            .join(Route, Route.id == NormalizedQuote.route_id)
            .join(Source, Source.id == NormalizedQuote.source_id)
            .where(
                NormalizedQuote.observation_date == day,
                NormalizedQuote.quality_flag == QualityFlag.VALID,
                NormalizedQuote.availability == AvailabilityStatus.AVAILABLE,
            )
        )
        return [
            (r, g, t, s, c) for r, g, t, s, c in self.session.execute(stmt).all() if t is not None
        ]

    def carrier_names(self) -> dict[str, str]:
        return dict(self.session.execute(select(Carrier.code, Carrier.name)).all())

    def latest_observation_date(self) -> date | None:
        return self.session.scalar(
            select(func.max(NormalizedQuote.observation_date)).where(
                NormalizedQuote.is_canonical.is_(True)
            )
        )
