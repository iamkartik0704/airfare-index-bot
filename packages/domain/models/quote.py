"""Quote models: what a parser yields and what the pipeline produces.

``RawFareQuote`` is the adapter output: field *strings exactly as the source
displayed them* (``"₹ 5,400"``, ``"Sold out"``, ``"6E 2134"``). No parsing or
coercion happens in adapters beyond locating the text — that is the pipeline's
job (doc 07 phase 2), which keeps parsers thin and makes raw data replayable.

``AirfareQuote`` is the canonical, source-independent observation (doc 06).
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from packages.domain.enums import AvailabilityStatus, Cabin, QualityFlag


class RawFareQuote(BaseModel):
    """One fare as extracted from a source response. All values are raw text."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    carrier: str | None = None
    flight_number: str | None = None
    fare_class: str | None = None
    departure_time: str | None = None
    arrival_time: str | None = None
    stops: str | None = None
    base_fare: str | None = None
    taxes: str | None = None
    airport_fees: str | None = None
    convenience_fee: str | None = None
    total_fare: str | None = None
    currency: str | None = None
    seats_left: str | None = None
    availability: str | None = None
    #: Source-specific leftovers worth keeping for audit (never used downstream).
    extra: dict[str, str] = Field(default_factory=dict)

    def to_payload(self) -> dict[str, Any]:
        return self.model_dump(exclude_none=True)


class FareBreakdown(BaseModel):
    """Monetary components in INR. ``None`` means the source did not display it."""

    model_config = ConfigDict(frozen=True)

    base_fare: Decimal | None = None
    taxes: Decimal | None = None
    airport_fees: Decimal | None = None  # UDF, ASF, PSF and similar airport charges
    convenience_fee: Decimal | None = None
    total_fare: Decimal | None = None

    @property
    def is_complete(self) -> bool:
        return self.base_fare is not None and self.taxes is not None


class AirfareQuote(BaseModel):
    """Canonical normalized observation (doc 06 ``AirfareQuote``)."""

    model_config = ConfigDict(frozen=True)

    source_id: str
    carrier: str = Field(pattern=r"^[A-Z0-9]{2}$")
    flight_number: str
    origin: str = Field(pattern=r"^[A-Z]{3}$")
    destination: str = Field(pattern=r"^[A-Z]{3}$")
    observation_date: date
    observed_at: datetime
    travel_date: date
    departure_at: datetime | None = None
    purchase_window: int = Field(ge=0)
    advance_purchase_days: int = Field(ge=0)
    fare_class: str
    fare_family: str | None = None
    cabin: Cabin
    fares: FareBreakdown
    currency: str = "INR"
    availability_status: AvailabilityStatus
    seats_left: int | None = Field(default=None, ge=0)
    stops: int | None = Field(default=None, ge=0)
    is_synthetic: bool = False
    quality_flag: QualityFlag = QualityFlag.VALID
    quality_reasons: tuple[str, ...] = ()
