"""Index and route response schemas."""

from __future__ import annotations

import datetime as dt
from decimal import Decimal

from pydantic import Field

from apps.api.schemas.common import ApiModel, DataOrigin
from packages.domain.enums import IndexFrequency, IndexScope


class IndexPoint(ApiModel):
    period_start: dt.date
    period_end: dt.date
    value: Decimal = Field(description="Quality-adjusted APIx, base period = 100")
    nominal_value: Decimal = Field(description="Laspeyres index without the hedonic term")
    rolling_value: Decimal | None = Field(None, description="Trailing mean (daily series only)")
    avg_fare: Decimal
    observation_count: int
    coverage_pct: Decimal
    imputed_share: Decimal
    is_synthetic: bool


class IndexSeries(ApiModel):
    frequency: IndexFrequency
    scope: IndexScope
    scope_key: str
    data_origin: DataOrigin
    base_period: tuple[dt.date, dt.date] | None
    items: list[IndexPoint]


class Headline(ApiModel):
    date: dt.date
    value: Decimal
    nominal_value: Decimal
    rolling_value: Decimal
    avg_fare: Decimal
    change_dod_pct: Decimal | None
    change_wow_pct: Decimal | None
    change_mom_pct: Decimal | None
    coverage_pct: Decimal
    imputed_share: Decimal
    observation_count: int
    base_period: tuple[dt.date, dt.date] | None
    computed_at: dt.datetime | None
    data_origin: DataOrigin
    methodology_status: dict[str, str]


class SubIndex(ApiModel):
    scope: IndexScope
    scope_key: str
    value: Decimal
    change_pct: Decimal | None
    avg_fare: Decimal


class SubIndices(ApiModel):
    date: dt.date
    data_origin: DataOrigin
    items: list[SubIndex]


class LineageCell(ApiModel):
    route: str
    purchase_window: int
    median_fare: Decimal
    quote_count: int
    source_count: int
    imputed: bool
    imputed_from_date: dt.date | None
    is_synthetic: bool


class Lineage(ApiModel):
    date: dt.date
    index_value: Decimal
    index_run_id: str
    computed_at: dt.datetime | None
    parameters: dict[str, object]
    cells: list[LineageCell]
    quotes_endpoint: str


class RouteSummary(ApiModel):
    code: str
    origin: str
    destination: str
    distance_km: int
    region: str
    weight: Decimal
    weight_share_pct: Decimal
    latest_index: Decimal | None
    latest_avg_fare: Decimal | None
    change_mom_pct: Decimal | None


class LeadTimePointOut(ApiModel):
    purchase_window: int
    fare: Decimal
    premium_pct: Decimal


class LeadTimeOut(ApiModel):
    date: dt.date
    route: str | None
    elasticity: float | None = Field(description="Slope of ln(fare) on ln(days ahead)")
    cheapest_window: int | None
    data_origin: DataOrigin
    points: list[LeadTimePointOut]


class RouteTrends(ApiModel):
    route: RouteSummary
    lead_time: LeadTimeOut
    history: list[IndexPoint]
    data_origin: DataOrigin
