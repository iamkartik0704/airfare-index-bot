"""Index-side domain records (doc 06 ``IndexObservation``, doc 09).

These are the typed inputs/outputs of the pure index engine. They carry no ORM
state so the engine can run offline for backtesting (doc 09 "interface
boundaries").
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from packages.domain.enums import ImputationMethod, IndexFrequency, IndexScope


class PriceCell(BaseModel):
    """Canonical quotes collapsed for one (date, route, window) — the engine input."""

    model_config = ConfigDict(frozen=True)

    observation_date: date
    route_code: str
    purchase_window: int
    fares: tuple[Decimal, ...]
    quality_factors: tuple[Decimal, ...]
    source_count: int = 0
    is_synthetic: bool = False


class IndexObservation(BaseModel):
    """Elementary aggregate: median fare per (date, route, window) (doc 06/08)."""

    model_config = ConfigDict(frozen=True)

    observation_date: date
    route_code: str
    purchase_window: int
    median_fare: Decimal
    mean_fare: Decimal
    min_fare: Decimal
    max_fare: Decimal
    quote_count: int
    source_count: int
    quality_factor: Decimal
    imputed: bool = False
    imputation_method: ImputationMethod = ImputationMethod.NONE
    imputed_from_date: date | None = None
    is_synthetic: bool = False


class IndexValue(BaseModel):
    """A published index number for a period and scope."""

    model_config = ConfigDict(frozen=True)

    frequency: IndexFrequency
    scope: IndexScope
    scope_key: str = ""
    period_start: date
    period_end: date
    value: Decimal = Field(description="Quality-adjusted (hedonic) index, base = 100")
    nominal_value: Decimal = Field(description="Pure Laspeyres, no quality adjustment")
    avg_fare: Decimal
    observation_count: int
    coverage_pct: Decimal
    imputed_share: Decimal
    is_synthetic: bool = False
