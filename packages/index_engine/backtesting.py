"""Back-testing APIx against DGCA monthly average fares (ps.md, docs 01, 14).

Two comparisons are produced:

* **daily** — each day's basket average fare against its month's DGCA average
  fare (absolute percentage error per day). ps.md asks for at least 30 days of
  back-tested results: ``days_covered`` counts days that have a benchmark.
* **monthly** — the month's mean of daily basket fares against the DGCA figure:
  Pearson and Spearman correlation, MAPE and directional accuracy of
  month-on-month moves (each needs ≥ 3 months to be meaningful).

Level differences are expected (APIx prices a fixed basket across five
purchase windows; DGCA averages all tickets sold), so co-movement
(correlation, direction) is the primary signal and doc 14's target is
Pearson r > 0.95. The verdict always states whether either side is synthetic.
"""

from __future__ import annotations

import math
from collections import defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from statistics import mean
from typing import Any

MIN_DAYS = 30
PEARSON_TARGET = 0.95


@dataclass(frozen=True)
class ComparisonPoint:
    granularity: str  # DAY | MONTH
    period: date
    apix_avg_fare: Decimal
    apix_index: Decimal | None
    benchmark_avg_fare: Decimal
    abs_pct_error: Decimal


@dataclass
class BacktestResult:
    points: list[ComparisonPoint]
    metrics: dict[str, Any] = field(default_factory=dict)
    verdict: str = ""


def pearson(xs: Sequence[float], ys: Sequence[float]) -> float | None:
    n = len(xs)
    if n < 3:
        return None
    mx, my = mean(xs), mean(ys)
    sxy = sum((x - mx) * (y - my) for x, y in zip(xs, ys, strict=True))
    sxx = sum((x - mx) ** 2 for x in xs)
    syy = sum((y - my) ** 2 for y in ys)
    if sxx == 0 or syy == 0:
        return None
    return sxy / math.sqrt(sxx * syy)


def _ranks(values: Sequence[float]) -> list[float]:
    order = sorted(range(len(values)), key=lambda i: values[i])
    ranks = [0.0] * len(values)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and values[order[j + 1]] == values[order[i]]:
            j += 1
        for k in range(i, j + 1):
            ranks[order[k]] = (i + j) / 2 + 1
        i = j + 1
    return ranks


def spearman(xs: Sequence[float], ys: Sequence[float]) -> float | None:
    return pearson(_ranks(xs), _ranks(ys)) if len(xs) >= 3 else None


def directional_accuracy(xs: Sequence[float], ys: Sequence[float]) -> float | None:
    if len(xs) < 3:
        return None
    hits = sum(
        1
        for i in range(1, len(xs))
        if (xs[i] - xs[i - 1]) * (ys[i] - ys[i - 1]) > 0
        or (xs[i] == xs[i - 1] and ys[i] == ys[i - 1])
    )
    return hits / (len(xs) - 1)


def _ape(actual: Decimal, benchmark: Decimal) -> Decimal:
    return (Decimal(100) * abs(actual - benchmark) / benchmark).quantize(Decimal("0.0001"))


def run_backtest(
    daily: Mapping[date, tuple[Decimal, Decimal | None]],
    benchmark: Mapping[date, Decimal],
    *,
    apix_synthetic: bool,
    benchmark_synthetic: bool,
    benchmark_label: str,
) -> BacktestResult:
    """``daily``: day → (basket avg fare, headline index). ``benchmark``: month start → fare."""
    points: list[ComparisonPoint] = []
    by_month: dict[date, list[tuple[Decimal, Decimal | None]]] = defaultdict(list)
    for day in sorted(daily):
        month = day.replace(day=1)
        bench = benchmark.get(month)
        if bench is None or bench <= 0:
            continue
        fare, index = daily[day]
        points.append(ComparisonPoint("DAY", day, fare, index, bench, _ape(fare, bench)))
        by_month[month].append((fare, index))

    months = sorted(by_month)
    monthly_fares = [
        sum((f for f, _ in by_month[m]), Decimal(0)) / len(by_month[m]) for m in months
    ]
    for month, fare in zip(months, monthly_fares, strict=True):
        indices = [i for _, i in by_month[month] if i is not None]
        points.append(
            ComparisonPoint(
                "MONTH",
                month,
                fare.quantize(Decimal("0.01")),
                (sum(indices, Decimal(0)) / len(indices)).quantize(Decimal("0.0001"))
                if indices
                else None,
                benchmark[month],
                _ape(fare, benchmark[month]),
            )
        )

    day_points = [p for p in points if p.granularity == "DAY"]
    xs = [float(f) for f in monthly_fares]
    ys = [float(benchmark[m]) for m in months]
    r = pearson(xs, ys)
    metrics: dict[str, Any] = {
        "days_covered": len(day_points),
        "months_covered": len(months),
        "daily_mape_pct": float(mean(float(p.abs_pct_error) for p in day_points))
        if day_points
        else None,
        "monthly_mape_pct": (
            float(mean(float(p.abs_pct_error) for p in points if p.granularity == "MONTH"))
            if months
            else None
        ),
        "pearson": r,
        "spearman": spearman(xs, ys),
        "directional_accuracy": directional_accuracy(xs, ys),
        "mean_bias_pct": (
            float(
                mean(float(100 * (p.apix_avg_fare / p.benchmark_avg_fare - 1)) for p in day_points)
            )
            if day_points
            else None
        ),
        "pearson_target": PEARSON_TARGET,
        "min_days_required": MIN_DAYS,
    }
    return BacktestResult(
        points, metrics, _verdict(metrics, apix_synthetic, benchmark_synthetic, benchmark_label)
    )


def _verdict(
    metrics: Mapping[str, Any], apix_synthetic: bool, benchmark_synthetic: bool, label: str
) -> str:
    caveat = ""
    if apix_synthetic or benchmark_synthetic:
        sides = [
            n for n, s in (("APIx data", apix_synthetic), ("benchmark", benchmark_synthetic)) if s
        ]
        caveat = (
            f" [SYNTHETIC: {' and '.join(sides)} — demonstrates the method, "
            "not real-world accuracy]"
        )
    days = metrics["days_covered"]
    if days < MIN_DAYS:
        return f"INSUFFICIENT: {days} of {MIN_DAYS} required days benchmarked ({label}){caveat}"
    r = metrics["pearson"]
    if r is None:
        return (
            f"PARTIAL: {days} days back-tested, daily MAPE {metrics['daily_mape_pct']:.1f}%; "
            f"correlation needs ≥3 benchmark months ({label}){caveat}"
        )
    status = "PASS" if r >= PEARSON_TARGET else "FAIL"
    return (
        f"{status}: Pearson r={r:.3f} over {metrics['months_covered']} months, {days} days, "
        f"monthly MAPE {metrics['monthly_mape_pct']:.1f}% ({label}){caveat}"
    )
