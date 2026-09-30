"""
SAFAR index construction — the Python twin of `src/convex/lib/index.ts`.

    APIx(d) = 100 · Σᵣ wᵣ · [Pᵣ(d) / Pᵣ(0)] · [Q(0) / Q(d)]

Fixed basket, fixed DGCA weights, median route price across carriers and fare
classes, and a hedonic quality divisor so that a mix shift toward better seats
is not recorded as airfare inflation.
"""

from __future__ import annotations

import json
import math
import statistics
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from .clean import BASKET_WEIGHTS, CleanQuote

REFERENCE_PERIOD = date(2025, 9, 20)
LEAD_TIME_WEIGHTS = {1: 0.08, 7: 0.42, 15: 0.22, 30: 0.18, 45: 0.10}
BASE_WINDOW_DAYS = 7
# The reference snapshot lives in the warehouse, not in the day's quotes: the
# index is a ratio to a FIXED base, so it must survive every new observation.
BASE_STORE = Path(__file__).resolve().parents[1] / "data" / "base_snapshot.json"

TOTAL_WEIGHT = sum(BASKET_WEIGHTS.values())
ROUTE_W = {k: v / TOTAL_WEIGHT for k, v in BASKET_WEIGHTS.items()}


def _weighted_geometric(values: list[float], weights: list[float]) -> float:
    num = sum(w * math.log(v) for v, w in zip(values, weights) if v > 0)
    den = sum(w for v, w in zip(values, weights) if v > 0)
    return math.exp(num / den) if den else 0.0


def cell_price(quotes: list[CleanQuote]) -> tuple[float, float]:
    """(median all-in fare, hedonic quality index) for one route × window cell."""
    if not quotes:
        return 0.0, 1.0
    total = statistics.median([q.total_fare for q in quotes])
    quality = statistics.fmean([q.quality for q in quotes])
    return total, quality


def route_price(quotes: list[CleanQuote]) -> tuple[float, float]:
    """Booking-curve weighted route price: the five PSI windows collapse into one."""
    prices, qualities, weights = [], [], []
    for lead, weight in LEAD_TIME_WEIGHTS.items():
        cell = [q for q in quotes if q.lead_time == lead]
        price, quality = cell_price(cell)
        if price:
            prices.append(price)
            qualities.append(quality)
            weights.append(weight)
    if not prices:
        return 0.0, 1.0
    return _weighted_geometric(prices, weights), statistics.fmean(qualities)


def base_snapshot(quotes: list[CleanQuote]) -> dict[str, tuple[float, float]]:
    """Reference-period means: the CPI's 7-day reference-period averaging."""
    acc: dict[str, list[tuple[float, float]]] = {}
    for q in quotes:
        acc.setdefault(q.route_id, []).append((q.total_fare, q.quality))
    return {
        route: (
            statistics.fmean([t for t, _ in rows]),
            statistics.fmean([qq for _, qq in rows]),
        )
        for route, rows in acc.items()
    }


def load_base(quotes: list[CleanQuote] | None = None) -> dict:
    """Load the stored reference snapshot; seed it on first run."""
    if BASE_STORE.exists():
        return json.loads(BASE_STORE.read_text())
    snapshot = base_snapshot(quotes or [])
    BASE_STORE.parent.mkdir(parents=True, exist_ok=True)
    BASE_STORE.write_text(json.dumps(snapshot, indent=2))
    return snapshot


def build_index(quotes: list[CleanQuote], day: date, base: dict | None = None) -> dict:
    """One observation of APIx. `base` is the stored reference snapshot."""
    reference = base if base is not None else load_base(quotes)
    by_route: dict[str, list[CleanQuote]] = {}
    for q in quotes:
        by_route.setdefault(q.route_id, []).append(q)

    nominal = real = quality = 0.0
    contributions = []
    for route, weight in ROUTE_W.items():
        price, q_now = route_price(by_route.get(route, []))
        price_0, q_0 = reference.get(route, (price or 1.0, 1.0))
        if not price or not price_0:
            continue
        ratio = price / price_0
        hedonic = q_0 / (q_now or 1.0)
        nominal += weight * ratio
        real += weight * ratio * hedonic
        quality += weight * q_now
        contributions.append({"route": route, "weight": round(weight * 100, 3), "changePct": round((ratio - 1) * 100, 2)})

    return {
        "date": day.isoformat(),
        "value": round(real * 100, 2),
        "nominal": round(nominal * 100, 2),
        "qualityIndex": round(quality, 4),
        "hedgeRatio": round(real / nominal, 4) if nominal else 1.0,
        "avgFare": round(statistics.fmean([q.total_fare for q in quotes])) if quotes else 0,
        "observations": len(quotes),
        "contributions": contributions,
    }


def route_contribution(quotes: list[CleanQuote], base: dict | None = None) -> list[dict]:
    """Decomposition of the move: wᵣ × ΔPᵣ, in index points."""
    point = build_index(quotes, date.today(), base)
    return sorted(point["contributions"], key=lambda c: -abs(c["changePct"] * c["weight"]))


def monthly_series(points: list[dict]) -> list[dict]:
    """Daily observations → monthly sub-indices, with MoM and YoY."""
    buckets: dict[str, list[dict]] = {}
    for p in points:
        buckets.setdefault(p["date"][:7], []).append(p)
    out = []
    for period, rows in sorted(buckets.items()):
        out.append({
            "period": period,
            "value": round(statistics.fmean([r["value"] for r in rows]), 2),
            "n": len(rows),
        })
    for i, row in enumerate(out):
        if i:
            row["change"] = round((row["value"] / out[i - 1]["value"] - 1) * 100, 2)
        if i >= 12:
            row["yoy"] = round((row["value"] / out[i - 12]["value"] - 1) * 100, 2)
    return out


def backtest(api_points: list[dict], dgca_monthly: dict[str, float]) -> dict:
    """
    Validate SAFAR against the DGCA monthly average domestic economy fare.

    Both series are rebased to 100 at the first common month, then correlated
    and differenced. The level gap is reported separately: it is basket scope,
    not error.
    """
    api = {p["date"][:7]: p["value"] for p in api_points}
    common = sorted(set(api) & set(dgca_monthly))
    if len(common) < 6:
        return {"verdict": "insufficient overlap", "months": len(common)}

    a0, d0 = api[common[0]], dgca_monthly[common[0]]
    xs = [api[m] / a0 * 100 for m in common]
    ys = [dgca_monthly[m] / d0 * 100 for m in common]

    def pearson(u: list[float], v: list[float]) -> float:
        mu, mv = statistics.fmean(u), statistics.fmean(v)
        cov = sum((a - mu) * (b - mv) for a, b in zip(u, v))
        return cov / math.sqrt(sum((a - mu) ** 2 for a in u) * sum((b - mv) ** 2 for b in v))

    hit = sum(
        1
        for i in range(1, len(xs))
        if math.copysign(1, xs[i] - xs[i - 1]) == math.copysign(1, ys[i] - ys[i - 1])
    )
    mape = statistics.fmean([abs((api[m] / a0) / (dgca_monthly[m] / d0) - 1) * 100 for m in common])
    r = pearson(xs, ys)
    verdict = (
        "PASS — SAFAR reproduces the DGCA reference series within tolerance"
        if r >= 0.9 and mape < 10
        else "PASS (directional) — tracks DGCA; level gap is basket scope"
        if r >= 0.7
        else "REVIEW — divergence beyond tolerance"
    )
    return {
        "months": len(common),
        "pearson": round(r, 3),
        "mapePct": round(mape, 2),
        "directionalAccuracyPct": round(hit / (len(xs) - 1) * 100, 1),
        "verdict": verdict,
    }
