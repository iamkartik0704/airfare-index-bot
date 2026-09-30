"""Deduplication keys and canonical selection (doc 07 phase 3).

Two notions of "the same fare":

* **dedup_key** — within one source: source | carrier | flight | fare family
  (the source's own product label, falling back to the fare class) | travel
  date | observation date. Repeated observations on the same day
  (a duplicated listing, an intra-day re-sweep, a retried job) collapse to
  the latest one ("latest wins", doc 07); the others are flagged
  ``DUPLICATE`` but kept.
* **group_key** — across channels: carrier | flight | fare class | travel
  date | observation date. The same IndiGo fare seen on goindigo.in and on an
  OTA is one market price; exactly one row per group is ``is_canonical`` and
  feeds the index. Preference: a usable (VALID, AVAILABLE) row, then the
  source with the lowest ``channel_priority`` (airline direct), then the most
  recent observation, then the lowest id (deterministic).
"""

from __future__ import annotations

import hashlib
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, datetime

from packages.domain.enums import AvailabilityStatus, QualityFlag


def _digest(*parts: object) -> str:
    return hashlib.sha256("|".join(str(p) for p in parts).encode()).hexdigest()


def dedup_key(
    source_id: str,
    carrier: str,
    flight_number: str,
    fare_product: str,
    travel_date: date,
    observation_date: date,
) -> str:
    product = " ".join(fare_product.upper().split())
    return _digest(source_id, carrier, flight_number, product, travel_date, observation_date)


def group_key(
    carrier: str, flight_number: str, fare_class: str, travel_date: date, observation_date: date
) -> str:
    return _digest(carrier, flight_number, fare_class, travel_date, observation_date)


@dataclass(frozen=True)
class CanonicalCandidate:
    row_id: int
    quality_flag: QualityFlag
    availability: AvailabilityStatus
    channel_priority: int
    observed_at: datetime


def choose_canonical(candidates: Sequence[CanonicalCandidate]) -> int | None:
    """Row id of the group's representative, or ``None`` for an empty group."""
    live = [c for c in candidates if c.quality_flag is not QualityFlag.DUPLICATE]
    if not live:
        return None

    def rank(c: CanonicalCandidate) -> tuple[int, int, float, int]:
        usable = (
            c.quality_flag is QualityFlag.VALID and c.availability is AvailabilityStatus.AVAILABLE
        )
        return (0 if usable else 1, c.channel_priority, -c.observed_at.timestamp(), c.row_id)

    return min(live, key=rank).row_id
