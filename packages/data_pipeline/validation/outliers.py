"""Outlier detection with the Median Absolute Deviation (doc 07 phase 4).

Applied per cell — (observation date, route, purchase window) — because a
T+1 DEL-BOM fare and a T+45 DEL-JAI fare are not comparable. A quote is an
outlier when

* its total is outside the configured absolute bounds (e.g. < ₹500), or
* the cell has at least ``min_group_size`` quotes and the modified z-score
  ``0.6745 · |x − median| / MAD`` exceeds ``threshold`` (Iglewicz–Hoaglin).

With MAD = 0 (all identical) nothing is an outlier by the robust test. The
function is pure; callers persist the resulting flags.
"""

from __future__ import annotations

from collections.abc import Sequence
from decimal import Decimal
from statistics import median

MAD_SCALE = Decimal("0.6745")


def modified_z_scores(values: Sequence[Decimal]) -> list[Decimal]:
    if not values:
        return []
    med = Decimal(median(values))
    mad = Decimal(median([abs(v - med) for v in values]))
    if mad == 0:
        return [Decimal(0) for _ in values]
    return [MAD_SCALE * abs(v - med) / mad for v in values]


def detect_outliers(
    totals: Sequence[Decimal],
    *,
    threshold: float,
    min_group_size: int,
    floor: Decimal,
    ceiling: Decimal,
) -> list[str | None]:
    """Reason code per value (``None`` = not an outlier)."""
    reasons: list[str | None] = [
        "BELOW_FARE_FLOOR" if t < floor else "ABOVE_FARE_CEILING" if t > ceiling else None
        for t in totals
    ]
    if len(totals) >= min_group_size:
        limit = Decimal(str(threshold))
        for i, z in enumerate(modified_z_scores(totals)):
            if reasons[i] is None and z > limit:
                reasons[i] = "MAD_OUTLIER"
    return reasons
