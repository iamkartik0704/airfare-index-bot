"""
SAFAR cleaning pipeline — the Python twin of `cleanQuotes()` in
`src/convex/lib/engine.ts`.

Every step is counted so the dashboard can show the funnel:

    raw → parse → de-duplicate → sold-out/cancelled drop → robust outlier
    rejection (median ± 3·MAD) → tax/fee decomposition → imputation of blocked
    cells (flagged) → PSI cell prices

MAD rather than standard deviation is deliberate: a genuine Diwali fare spike
must survive, a tariff glitch must not.
"""

from __future__ import annotations

import statistics
from dataclasses import asdict, dataclass, field

from .collect.base import RawQuote, parse_rupees

BASKET_WEIGHTS = {
    "DEL-BOM": 4.2, "DEL-BLR": 3.6, "DEL-HYD": 2.9, "BOM-BLR": 2.4, "DEL-CCU": 2.1,
    "BLR-HYD": 1.9, "MAA-DEL": 1.8, "BLR-COK": 1.7, "DEL-COK": 1.6, "DEL-JAI": 1.5,
    "HYD-BOM": 1.4, "DEL-PNQ": 1.3, "DEL-TRV": 1.1, "CCU-BLR": 1.1, "DEL-IXC": 1.0,
    "BLR-MAA": 1.0, "BOM-CCU": 1.0, "HYD-CCU": 0.9, "BOM-GOI": 0.9, "PNQ-BLR": 0.7,
    "CCU-PNQ": 0.6, "DEL-VNS": 0.6, "IDR-DEL": 0.6, "DEL-LKO": 0.5,
}
CARRIER_FARE_INDEX = {"6E": 0.97, "AI": 1.14, "QP": 0.90, "SG": 0.93, "IX": 0.88}
CONVENIENCE_FEE = {
    "makemytrip": 48, "yatra": 40, "easemytrip": 35,
    "cleartrip": 55, "ixigo": 42, "goibibo": 44,
}
FARE_CLASS_QUALITY = {"SAVER": 0.70, "VALUE": 0.95, "FLEX": 1.22, "PREMIUM": 1.55, "BIZ": 2.40}


@dataclass
class CleanQuote:
    source_id: str
    carrier: str
    route_id: str
    lead_time: int
    fare_class: str
    base_fare: float
    taxes: float
    udf: float
    convenience_fee: float
    total_fare: float
    quality: float
    flags: list[str] = field(default_factory=list)
    imputed: bool = False


@dataclass
class CleaningReport:
    rawCount: int
    keptCount: int
    droppedSoldOut: int
    droppedCancelled: int
    droppedDuplicate: int
    droppedOutlier: int
    droppedInvalid: int
    imputedCount: int
    coverage: float
    medianTotal: float
    madTotal: float

    def asdict(self) -> dict:
        return asdict(self)


def _median(xs: list[float]) -> float:
    return statistics.median(xs) if xs else 0.0


def _mad(xs: list[float]) -> float:
    """Median absolute deviation scaled to be a consistent estimator of sigma."""
    if not xs:
        return 0.0
    med = _median(xs)
    return 1.4826 * _median([abs(x - med) for x in xs])


def clean_quotes(raw: list[RawQuote]) -> tuple[list[CleanQuote], dict]:
    report = CleaningReport(
        rawCount=len(raw), keptCount=0, droppedSoldOut=0, droppedCancelled=0,
        droppedDuplicate=0, droppedOutlier=0, droppedInvalid=0, imputedCount=0,
        coverage=0.0, medianTotal=0.0, madTotal=0.0,
    )
    if not raw:
        return [], report.asdict()

    seen: set[tuple] = set()
    parsed: list[CleanQuote] = []

    for q in raw:
        if getattr(q, "sold_out", False) or q.seats_left == 0:
            report.droppedSoldOut += 1
            continue
        if getattr(q, "is_cancelled", False):
            report.droppedCancelled += 1
            continue
        dup_key = (q.source_id, q.carrier, q.route_id, q.lead_time, q.fare_class, q.fare_text)
        if dup_key in seen:
            report.droppedDuplicate += 1
            continue
        seen.add(dup_key)

        total = parse_rupees(q.fare_text)
        if total <= 0:
            report.droppedInvalid += 1
            continue

        fee = float(CONVENIENCE_FEE.get(q.source_id, 0))
        if "inclusive" in (q.tax_text or "").lower():
            taxes = round(total * 0.194)
        else:
            taxes = parse_rupees(q.tax_text)
        base = max(1.0, total - taxes - fee)

        flags = []
        if not q.refundable:
            flags.append("non-refundable")
        if q.baggage_kg <= 15:
            flags.append("no-check-in-bag")
        if q.source_id in CONVENIENCE_FEE:
            flags.append("ota-channel")

        parsed.append(
            CleanQuote(
                source_id=q.source_id,
                carrier=q.carrier,
                route_id=q.route_id,
                lead_time=q.lead_time,
                fare_class=q.fare_class,
                base_fare=round(base),
                taxes=round(taxes),
                udf=0.0,
                convenience_fee=fee,
                total_fare=round(base + taxes + fee),
                quality=FARE_CLASS_QUALITY.get(q.fare_class, 0.95),
                flags=flags,
            )
        )

    totals = [q.total_fare for q in parsed]
    med = _median(totals)
    sigma = max(_mad(totals), med * 0.01)
    lo, hi = med - 3 * sigma, med + 3 * sigma
    abs_lo, abs_hi = med * 0.45, med * 2.6

    kept = []
    for q in parsed:
        if q.total_fare < lo or q.total_fare > hi or q.total_fare < abs_lo or q.total_fare > abs_hi:
            report.droppedOutlier += 1
            continue
        kept.append(q)

    # Imputation: a carrier cell removed by an anti-bot block is refilled from
    # its own fare index against the cell median and flagged.
    present = {q.carrier for q in kept}
    for carrier, index in CARRIER_FARE_INDEX.items():
        if carrier in present or not kept:
            continue
        imputed_total = round(med * (index / 0.97))
        kept.append(
            CleanQuote(
                source_id="imputed", carrier=carrier, route_id=kept[0].route_id,
                lead_time=kept[0].lead_time, fare_class="VALUE",
                base_fare=round(imputed_total * 0.82), taxes=round(imputed_total * 0.18),
                udf=0.0, convenience_fee=0.0, total_fare=imputed_total,
                quality=0.95, flags=["imputed", "anti-bot-block"], imputed=True,
            )
        )
        report.imputedCount += 1

    report.keptCount = len(kept)
    report.medianTotal = round(med)
    report.madTotal = round(sigma)
    report.coverage = round(100 * len(kept) / report.rawCount, 2) if report.rawCount else 0.0
    return kept, report.asdict()
