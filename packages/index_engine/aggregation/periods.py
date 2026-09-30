"""Weekly and monthly indices from the daily series (decision D7).

Period values are the arithmetic mean of the daily values in the period —
the CPI period-average convention. ISO weeks run Monday–Sunday.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Callable, Sequence
from datetime import date, timedelta
from decimal import Decimal

from packages.domain.enums import IndexFrequency
from packages.domain.models.index import IndexValue


def week_start(day: date) -> date:
    return day - timedelta(days=day.weekday())


def month_start(day: date) -> date:
    return day.replace(day=1)


def _period_end(start: date, frequency: IndexFrequency) -> date:
    if frequency is IndexFrequency.WEEKLY:
        return start + timedelta(days=6)
    next_month = (start.replace(day=28) + timedelta(days=4)).replace(day=1)
    return next_month - timedelta(days=1)


def _mean(values: Sequence[Decimal]) -> Decimal:
    return sum(values, Decimal(0)) / len(values)


def roll_up(daily: Sequence[IndexValue], frequency: IndexFrequency) -> list[IndexValue]:
    if frequency is IndexFrequency.DAILY:
        return list(daily)
    key: Callable[[date], date] = week_start if frequency is IndexFrequency.WEEKLY else month_start
    buckets: dict[tuple[str, str, date], list[IndexValue]] = defaultdict(list)
    for value in daily:
        buckets[(value.scope.value, value.scope_key, key(value.period_start))].append(value)
    out: list[IndexValue] = []
    for (_, _, start), values in sorted(
        buckets.items(), key=lambda kv: (kv[0][2], kv[0][0], kv[0][1])
    ):
        first = values[0]
        out.append(
            IndexValue(
                frequency=frequency,
                scope=first.scope,
                scope_key=first.scope_key,
                period_start=start,
                period_end=_period_end(start, frequency),
                value=_mean([v.value for v in values]),
                nominal_value=_mean([v.nominal_value for v in values]),
                avg_fare=_mean([v.avg_fare for v in values]),
                observation_count=sum(v.observation_count for v in values),
                coverage_pct=_mean([v.coverage_pct for v in values]),
                imputed_share=_mean([v.imputed_share for v in values]),
                is_synthetic=any(v.is_synthetic for v in values),
            )
        )
    return out


def rolling_mean(values: Sequence[Decimal], window: int) -> list[Decimal]:
    out: list[Decimal] = []
    for i in range(len(values)):
        chunk = values[max(0, i - window + 1) : i + 1]
        out.append(_mean(chunk))
    return out
