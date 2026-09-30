"""Raw quote → canonical ``AirfareQuote`` (doc 07 phases 2–3).

Maps every source vocabulary onto one canonical one:

* carrier names/aliases → IATA code (``"IndiGo"``, ``"INDIGO"`` → ``6E``);
* fare families → the fare-class taxonomy (``"Flexi Plus"`` → ``ECONOMY_FLEX``);
* display strings → ``Decimal`` amounts, seat counts, stops, departure time;
* availability text → ``AvailabilityStatus``;
* the job's travel/observation dates → ``advance_purchase_days``.

Validation rules (doc 07 phase 2, ``validation.rules``) are applied here too,
so the result is either a canonical quote with quality reasons, or a
``NormalizationError`` describing why the raw record cannot be represented.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from zoneinfo import ZoneInfo

from packages.config.reference import FareClassDef, ReferenceData
from packages.data_pipeline.cleaning.cleaner import (
    normalize_flight_number,
    parse_departure,
    parse_first_int,
    parse_money,
    parse_stops,
)
from packages.data_pipeline.exceptions import CleaningError, NormalizationError
from packages.data_pipeline.validation.rules import validate_fares
from packages.domain.enums import AvailabilityStatus, Cabin, QualityFlag
from packages.domain.models.quote import AirfareQuote, FareBreakdown, RawFareQuote

IST = ZoneInfo("Asia/Kolkata")

_AVAILABILITY = {
    "AVAILABLE": AvailabilityStatus.AVAILABLE,
    "SOLD_OUT": AvailabilityStatus.SOLD_OUT,
    "SOLD OUT": AvailabilityStatus.SOLD_OUT,
    "SOLDOUT": AvailabilityStatus.SOLD_OUT,
    "FULL": AvailabilityStatus.SOLD_OUT,
    "CANCELLED": AvailabilityStatus.CANCELLED,
    "CANCELED": AvailabilityStatus.CANCELLED,
}


@dataclass(frozen=True)
class RawContext:
    """Where a raw quote came from — supplied by the job, not the parser."""

    source_id: str
    origin: str
    destination: str
    travel_date: date
    purchase_window: int
    observation_date: date
    observed_at: datetime
    is_synthetic: bool


class Normalizer:
    def __init__(self, reference: ReferenceData, *, total_tolerance: Decimal) -> None:
        self._carriers = reference.carrier_alias_map()
        self._classes: dict[str, FareClassDef] = {}
        for cls in reference.fare_classes.classes:
            for alias in (cls.code, cls.label, *cls.aliases):
                self._classes[_key(alias)] = cls
        self._default_class = next(
            c
            for c in reference.fare_classes.classes
            if c.code == reference.fare_classes.default_class
        )
        self._tolerance = total_tolerance

    def carrier_code(self, raw: str | None, flight_number: str | None) -> str:
        if raw:
            code = self._carriers.get(raw.strip().upper())
            if code:
                return code
        if flight_number and flight_number[:2] in self._carriers.values():
            return flight_number[:2]  # "AI 5395" identifies the carrier even without a name
        raise NormalizationError("unknown carrier", carrier=raw, flight=flight_number)

    def fare_class(self, raw: str | None) -> tuple[FareClassDef, list[str]]:
        if not raw:
            return self._default_class, ["FARE_CLASS_MISSING"]
        found = self._classes.get(_key(raw))
        if found is None:
            return self._default_class, ["FARE_CLASS_UNMAPPED"]
        return found, []

    def normalize(self, raw: RawFareQuote, ctx: RawContext) -> AirfareQuote:
        try:
            return self._normalize(raw, ctx)
        except CleaningError as exc:
            raise NormalizationError(exc.message, **exc.context) from exc

    def _normalize(self, raw: RawFareQuote, ctx: RawContext) -> AirfareQuote:
        flight = normalize_flight_number(raw.flight_number)
        if not flight:
            raise NormalizationError("flight number missing")
        carrier = self.carrier_code(raw.carrier, flight)
        availability = _AVAILABILITY.get((raw.availability or "AVAILABLE").strip().upper())
        if availability is None:
            raise NormalizationError("unknown availability status", value=raw.availability)
        fare_class, reasons = self.fare_class(raw.fare_class)

        fares = FareBreakdown(
            base_fare=parse_money(raw.base_fare),
            taxes=parse_money(raw.taxes),
            airport_fees=parse_money(raw.airport_fees),
            convenience_fee=parse_money(raw.convenience_fee),
            total_fare=parse_money(raw.total_fare),
        )
        if availability is AvailabilityStatus.AVAILABLE and fares.total_fare is None:
            raise NormalizationError("available fare without a total", flight=flight)
        if raw.currency and raw.currency.strip().upper() not in {"INR", "₹"}:
            raise NormalizationError("non-INR fare", currency=raw.currency)

        flag, rule_reasons = validate_fares(fares, availability, self._tolerance)
        departure_local = parse_departure(raw.departure_time, ctx.travel_date)
        return AirfareQuote(
            source_id=ctx.source_id,
            carrier=carrier,
            flight_number=flight,
            origin=ctx.origin,
            destination=ctx.destination,
            observation_date=ctx.observation_date,
            observed_at=ctx.observed_at,
            travel_date=ctx.travel_date,
            departure_at=departure_local.replace(tzinfo=IST) if departure_local else None,
            purchase_window=ctx.purchase_window,
            advance_purchase_days=max(0, (ctx.travel_date - ctx.observation_date).days),
            fare_class=fare_class.code,
            fare_family=(raw.fare_class or None),
            cabin=Cabin(fare_class.cabin),
            fares=fares,
            availability_status=availability,
            seats_left=parse_first_int(raw.seats_left),
            stops=parse_stops(raw.stops),
            is_synthetic=ctx.is_synthetic,
            quality_flag=flag,
            quality_reasons=tuple(reasons + rule_reasons),
        )

    def quality_factor(self, fare_class_code: str) -> Decimal:
        for cls in self._classes.values():
            if cls.code == fare_class_code:
                return cls.quality_factor
        return self._default_class.quality_factor


def _key(text: str) -> str:
    return " ".join(text.replace("_", " ").replace("-", " ").upper().split())


__all__ = ["IST", "Normalizer", "QualityFlag", "RawContext"]
