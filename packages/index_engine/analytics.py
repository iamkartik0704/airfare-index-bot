"""Analytical views over index observations (docs 09, 12): pure functions.

* **Lead-time curve & elasticity** — how the fare falls as the purchase is
  made further ahead. Elasticity is the slope of ln(fare) on ln(days ahead)
  (a constant-elasticity fit across T+1…T+45); −0.2 means booking 10 % further
  ahead lowers the fare by ≈2 %.
* **Sector heatmap** — route × period relative change.
* **Carrier / channel comparisons** — medians and premiums.
"""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from decimal import Decimal
from statistics import median


@dataclass(frozen=True)
class LeadTimePoint:
    purchase_window: int
    fare: Decimal
    premium_pct: Decimal  # vs the cheapest window


@dataclass(frozen=True)
class LeadTimeCurve:
    points: list[LeadTimePoint]
    elasticity: float | None
    cheapest_window: int | None


def ols_slope(xs: Sequence[float], ys: Sequence[float]) -> float | None:
    n = len(xs)
    if n < 2:
        return None
    mx, my = sum(xs) / n, sum(ys) / n
    sxx = sum((x - mx) ** 2 for x in xs)
    if sxx == 0:
        return None
    return sum((x - mx) * (y - my) for x, y in zip(xs, ys, strict=True)) / sxx


def lead_time_curve(fares_by_window: Mapping[int, Decimal]) -> LeadTimeCurve:
    windows = sorted(w for w, f in fares_by_window.items() if f > 0)
    if not windows:
        return LeadTimeCurve([], None, None)
    cheapest = min(windows, key=lambda w: fares_by_window[w])
    floor = fares_by_window[cheapest]
    points = [
        LeadTimePoint(
            purchase_window=w,
            fare=fares_by_window[w],
            premium_pct=(Decimal(100) * (fares_by_window[w] / floor - 1)).quantize(Decimal("0.01")),
        )
        for w in windows
    ]
    usable = [w for w in windows if w > 0]
    slope = ols_slope(
        [math.log(w) for w in usable], [math.log(float(fares_by_window[w])) for w in usable]
    )
    return LeadTimeCurve(points, None if slope is None else round(slope, 4), cheapest)


def weighted_window_fares(
    medians: Mapping[tuple[str, int], Decimal], route_weights: Mapping[str, Decimal]
) -> dict[int, Decimal]:
    """Basket-weighted fare per window from (route, window) medians."""
    acc: dict[int, tuple[Decimal, Decimal]] = {}
    for (route, window), fare in medians.items():
        weight = route_weights.get(route)
        if weight is None:
            continue
        total, wsum = acc.get(window, (Decimal(0), Decimal(0)))
        acc[window] = (total + weight * fare, wsum + weight)
    return {w: (t / ws).quantize(Decimal("0.01")) for w, (t, ws) in acc.items() if ws > 0}


@dataclass(frozen=True)
class HeatCell:
    route: str
    period: str
    value: Decimal
    change_pct: Decimal | None


def sector_heatmap(series: Mapping[str, Sequence[tuple[str, Decimal]]]) -> list[HeatCell]:
    """``series``: route → [(period label, index value)] in time order."""
    cells: list[HeatCell] = []
    for route, points in sorted(series.items()):
        previous: Decimal | None = None
        for period, value in points:
            change = None
            if previous is not None and previous != 0:
                change = (Decimal(100) * (value / previous - 1)).quantize(Decimal("0.01"))
            cells.append(HeatCell(route, period, value, change))
            previous = value
    return cells


def median_or_none(values: Sequence[Decimal]) -> Decimal | None:
    return Decimal(median(values)).quantize(Decimal("0.01")) if values else None


def premium_pct(value: Decimal | None, reference: Decimal | None) -> Decimal | None:
    if value is None or reference is None or reference == 0:
        return None
    return (Decimal(100) * (value / reference - 1)).quantize(Decimal("0.01"))
