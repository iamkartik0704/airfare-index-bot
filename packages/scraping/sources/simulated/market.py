"""Deterministic synthetic airfare market (decision D8).

Produces the *displayed* fares a traveller would see for a route, travel date
and observation date, so the whole pipeline can be demonstrated and
back-filled without touching real websites. Everything is a pure function of
its inputs (seeded hashing, no global RNG), so the same search always returns
the same page — a requirement for idempotent replays and deterministic tests.

The model is intentionally simple and is *not* an estimate of real Indian
fares: distance-based fare level × booking-curve (advance purchase) ×
day-of-week × festival seasonality × slow drift × carrier and fare-family
factors × noise. It also injects the real-world defects the pipeline must
handle: sold-out fares, cancelled flights, duplicated listings, and rare
garbled prices (outliers).
"""

from __future__ import annotations

import hashlib
import math
import random
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta

from packages.config.reference import Basket, CarrierDef

CARRIER_FACTOR = {"6E": 1.00, "AI": 1.12, "IX": 0.93, "QP": 0.95, "SG": 0.96}
FAMILIES_LCC = (("Saver", 1.00), ("Standard", 1.12), ("Flexi", 1.30))
FAMILIES_FSC = (("Economy Value", 1.00), ("Economy Classic", 1.15), ("Economy Flex", 1.34))
METRO_AIRPORTS = frozenset({"DEL", "BOM", "BLR", "HYD", "MAA", "CCU"})
DRIFT_PER_DAY = 0.00018  # ≈ 6.8 % a year
FESTIVAL_PEAKS = ((10, 28, 0.20, 12.0), (12, 27, 0.18, 7.0), (5, 30, 0.10, 20.0))


@dataclass(frozen=True)
class SimFlight:
    carrier: str
    flight_number: str
    departure: time
    duration_min: int


@dataclass(frozen=True)
class SimFare:
    carrier_name: str
    flight_number: str
    departure: time
    arrival: time
    fare_family: str
    base_fare: float
    taxes: float
    airport_fees: float
    convenience_fee: float
    total_fare: float
    seats_left: int | None
    status: str  # Available | Sold out | Cancelled


def _rng(*parts: object) -> random.Random:
    digest = hashlib.sha256("|".join(map(str, parts)).encode()).digest()
    return random.Random(int.from_bytes(digest[:8], "big"))


def lead_time_multiplier(advance_days: int) -> float:
    a = max(advance_days, 0)
    return 1.0 + 0.9 * math.exp(-a / 4.0) + 0.10 * max(0, 21 - a) / 21.0


def seasonality(travel_date: date) -> float:
    boost = 0.0
    for month, day, amplitude, width in FESTIVAL_PEAKS:
        peak = date(travel_date.year, month, day)
        for candidate in (peak, peak.replace(year=peak.year - 1), peak.replace(year=peak.year + 1)):
            gap = (travel_date - candidate).days
            boost += amplitude * math.exp(-((gap / width) ** 2))
    return 1.0 + boost


def weekday_factor(travel_date: date) -> float:
    return {4: 1.08, 6: 1.08, 1: 0.95, 2: 0.95}.get(travel_date.weekday(), 1.0)


class MarketModel:
    def __init__(self, basket: Basket, carriers: list[CarrierDef], seed: str = "safar-sim-v1"):
        self._routes = {r.code: r for r in basket.routes}
        self._carriers = {c.code: c for c in carriers}
        self._seed = seed
        self._epoch = date(2026, 1, 1)

    def schedule(self, route_code: str) -> list[SimFlight]:
        """Stable weekly timetable per route (same every day, like a real schedule)."""
        route = self._routes[route_code]
        rng = _rng(self._seed, "schedule", route_code)
        flights: list[SimFlight] = []
        codes = sorted(self._carriers)
        operating = [c for c in codes if rng.random() < 0.65] or codes[:2]
        if len(operating) < 2:
            operating = sorted({*operating, codes[0], codes[1]})
        duration = int(45 + route.distance_km / 11)
        for carrier in operating:
            for _ in range(rng.randint(1, 4)):
                dep = time(rng.randint(5, 22), rng.choice((0, 5, 15, 20, 30, 40, 45, 55)))
                number = f"{carrier}{rng.randint(100, 6999)}"
                flights.append(SimFlight(carrier, number, dep, duration))
        return sorted(flights, key=lambda f: (f.departure, f.flight_number))

    def fares(
        self, route_code: str, travel_date: date, observation_date: date, channel: str
    ) -> list[SimFare]:
        route = self._routes[route_code]
        advance = (travel_date - observation_date).days
        level = (1500 + 2.6 * route.distance_km) * lead_time_multiplier(advance)
        level *= seasonality(travel_date) * weekday_factor(travel_date)
        level *= 1 + DRIFT_PER_DAY * (observation_date - self._epoch).days
        level *= 1 + 0.03 * math.sin((observation_date - self._epoch).days / 29.5 * 2 * math.pi)
        airport_base = 390.0 if route.origin in METRO_AIRPORTS else 260.0

        fares: list[SimFare] = []
        for flight in self.schedule(route_code):
            key = (self._seed, route_code, flight.flight_number, travel_date, observation_date)
            rng = _rng(*key, channel)
            arrival = (
                datetime.combine(travel_date, flight.departure)
                + timedelta(minutes=flight.duration_min)
            ).time()
            carrier = self._carriers[flight.carrier]
            families = FAMILIES_FSC if carrier.group == "FSC" else FAMILIES_LCC
            flight_rng = _rng(*key)  # channel-independent: same flight state on every channel
            if flight_rng.random() < 0.005:
                fares.append(
                    _status_fare(carrier.name, flight, arrival, families[0][0], "Cancelled")
                )
                continue
            flight_sold_out = flight_rng.random() < 0.01 + 0.15 * math.exp(-advance / 2.0)
            for family, factor in families:
                if flight_sold_out or (
                    family == families[0][0]
                    and flight_rng.random() < 0.02 + 0.25 * math.exp(-advance / 3.0)
                ):
                    fares.append(_status_fare(carrier.name, flight, arrival, family, "Sold out"))
                    continue
                noise = math.exp(flight_rng.gauss(0.0, 0.06))
                base = level * CARRIER_FACTOR.get(flight.carrier, 1.0) * factor * noise
                if channel == "ota":
                    base *= 1 - rng.uniform(0.0, 0.03)
                base = round(base)
                taxes = round(base * 0.05)
                airport = round(airport_base + flight_rng.uniform(-20, 20))
                convenience = round(rng.uniform(299, 449)) if channel == "ota" else 0
                total = base + taxes + airport + convenience
                seats = flight_rng.randint(1, 9) if advance < 10 else None
                fare = SimFare(
                    carrier.name,
                    flight.flight_number,
                    flight.departure,
                    arrival,
                    family,
                    base,
                    taxes,
                    airport,
                    convenience,
                    total,
                    seats,
                    "Available",
                )
                if rng.random() < 0.004:  # stale/garbled card: every amount off by 10x
                    fare = _scaled(fare, 10.0)
                fares.append(fare)
                if rng.random() < 0.005:  # the same card listed twice
                    fares.append(fare)
        return fares


def _status_fare(
    carrier: str, flight: SimFlight, arrival: time, family: str, status: str
) -> SimFare:
    return SimFare(
        carrier,
        flight.flight_number,
        flight.departure,
        arrival,
        family,
        0.0,
        0.0,
        0.0,
        0.0,
        0.0,
        None,
        status,
    )


def _scaled(fare: SimFare, k: float) -> SimFare:
    return SimFare(
        fare.carrier_name,
        fare.flight_number,
        fare.departure,
        fare.arrival,
        fare.fare_family,
        fare.base_fare * k,
        fare.taxes * k,
        fare.airport_fees * k,
        fare.convenience_fee * k,
        fare.total_fare * k,
        fare.seats_left,
        fare.status,
    )
