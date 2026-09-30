"""Fixed-basket Laspeyres price relatives with hedonic quality adjustment (doc 09).

    APIx(d) = 100 · Σᵣ Wᵣ · (Pᵣ,d / Pᵣ,0) · (Q₀ / Q_d)

* ``Wᵣ`` fixed basket weights, re-normalised over the routes priced on ``d``;
* ``Pᵣ,d`` route price on ``d``, ``Pᵣ,0`` its base-period price;
* ``Q_d`` the weight-averaged quality factor of the fares observed on ``d``,
  ``Q₀`` its base-period value. Dividing by ``Q_d / Q₀`` removes price movement
  caused by a richer fare mix rather than dearer fares.

The nominal value (no quality term) is always computed alongside.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from decimal import Decimal

HUNDRED = Decimal(100)


@dataclass(frozen=True)
class RoutePoint:
    price: Decimal
    quality: Decimal


@dataclass(frozen=True)
class LaspeyresResult:
    value: Decimal
    nominal: Decimal
    avg_fare: Decimal
    weight_covered: Decimal  # share of basket weight priced (0–1)


def laspeyres(
    current: Mapping[str, RoutePoint],
    base: Mapping[str, RoutePoint],
    weights: Mapping[str, Decimal],
    *,
    hedonic: bool,
) -> LaspeyresResult | None:
    """``None`` when no basket route is priced both now and in the base period."""
    priced = [r for r in weights if r in current and r in base and base[r].price > 0]
    if not priced:
        return None
    weight_sum = sum((weights[r] for r in priced), Decimal(0))
    relative = sum((weights[r] * current[r].price / base[r].price for r in priced), Decimal(0))
    relative /= weight_sum
    q_now = sum((weights[r] * current[r].quality for r in priced), Decimal(0)) / weight_sum
    q_base = sum((weights[r] * base[r].quality for r in priced), Decimal(0)) / weight_sum
    quality_term = (q_base / q_now) if hedonic and q_now > 0 else Decimal(1)
    avg_fare = sum((weights[r] * current[r].price for r in priced), Decimal(0)) / weight_sum
    total_weight = sum(weights.values(), Decimal(0))
    return LaspeyresResult(
        value=HUNDRED * relative * quality_term,
        nominal=HUNDRED * relative,
        avg_fare=avg_fare,
        weight_covered=weight_sum / total_weight if total_weight else Decimal(0),
    )
