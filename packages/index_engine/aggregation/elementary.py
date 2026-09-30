"""Elementary aggregates: median fare per (date, route, window) (doc 09 §1).

The median resists outlier shocks such as the last flex seat on a flight.
Cells below ``min_quotes`` produce no observation (they become candidates for
imputation instead).
"""

from __future__ import annotations

from collections.abc import Iterable
from decimal import ROUND_HALF_UP, Decimal
from statistics import median

from packages.domain.models.index import IndexObservation, PriceCell

CENT = Decimal("0.01")
FOUR = Decimal("0.0001")


def summarize(cell: PriceCell) -> IndexObservation:
    fares = sorted(cell.fares)
    quality = cell.quality_factors or (Decimal(1),)
    return IndexObservation(
        observation_date=cell.observation_date,
        route_code=cell.route_code,
        purchase_window=cell.purchase_window,
        median_fare=Decimal(median(fares)).quantize(CENT, rounding=ROUND_HALF_UP),
        mean_fare=(sum(fares, Decimal(0)) / len(fares)).quantize(CENT, rounding=ROUND_HALF_UP),
        min_fare=fares[0],
        max_fare=fares[-1],
        quote_count=len(fares),
        source_count=cell.source_count,
        quality_factor=(sum(quality, Decimal(0)) / len(quality)).quantize(FOUR),
        is_synthetic=cell.is_synthetic,
    )


def build_observations(
    cells: Iterable[PriceCell], *, min_quotes: int = 1
) -> list[IndexObservation]:
    return [summarize(c) for c in cells if len(c.fares) >= max(1, min_quotes)]
