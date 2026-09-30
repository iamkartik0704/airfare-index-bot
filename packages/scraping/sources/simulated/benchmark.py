"""A synthetic monthly benchmark for demos (decision D9). NOT DGCA data.

Computed straight from the simulator's market model — the mean non-stop
economy fare across every flight, fare family and booking day of the month —
scaled to a lower level (a published average includes cheap early bookings
beyond T+45) and perturbed by seeded noise. It exists only so the back-test
machinery can be demonstrated end to end; every row is stored with
``is_synthetic=True`` and the label below, and the dashboard shows it.
"""

from __future__ import annotations

import hashlib
import random
from datetime import date, timedelta
from decimal import Decimal

from packages.config.reference import ReferenceData
from packages.domain.repositories.benchmarks import BenchmarkRecord
from packages.scraping.sources.simulated.market import MarketModel

LABEL = "SYNTHETIC DEMO BENCHMARK — not DGCA data"
LEVEL = 0.82
LEADS = (3, 10, 21, 35, 60)


def synthetic_monthly_benchmark(
    reference: ReferenceData, months: list[date]
) -> list[BenchmarkRecord]:
    market = MarketModel(reference.basket, reference.carriers)
    weights = reference.basket.normalized_weights()
    records: list[BenchmarkRecord] = []
    for month in sorted({m.replace(day=1) for m in months}):
        seed = int(hashlib.sha256(f"benchmark|{month}".encode()).hexdigest()[:8], 16)
        rng = random.Random(seed)
        total = Decimal(0)
        for route in reference.basket.routes:
            fares: list[float] = []
            for offset in range(0, 28, 3):  # sample booking days through the month
                booked = month + timedelta(days=offset)
                for lead in LEADS:
                    fares.extend(
                        f.total_fare
                        for f in market.fares(
                            route.code, booked + timedelta(days=lead), booked, "direct"
                        )
                        if f.status == "Available" and f.total_fare < 150_000
                    )
            if fares:
                total += weights[route.code] * Decimal(str(sum(fares) / len(fares)))
        noisy = float(total) * LEVEL * (1 + rng.gauss(0, 0.015))
        records.append(
            BenchmarkRecord(
                period_month=month,
                route_code="ALL",
                avg_fare=Decimal(str(round(noisy, 2))),
                source_label=LABEL,
                source_url=None,
                is_synthetic=True,
            )
        )
    return records
