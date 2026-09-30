"""Record-level validation rules (doc 07 phase 2).

Returns a quality flag plus machine-readable reason codes. A failed rule never
deletes data; it marks the canonical row ``INVALID`` so it is excluded from
the index but still visible for audit.
"""

from __future__ import annotations

from decimal import Decimal

from packages.domain.enums import AvailabilityStatus, QualityFlag
from packages.domain.models.quote import FareBreakdown


def validate_fares(
    fares: FareBreakdown, availability: AvailabilityStatus, tolerance: Decimal
) -> tuple[QualityFlag, list[str]]:
    reasons: list[str] = []
    if availability is not AvailabilityStatus.AVAILABLE:
        return QualityFlag.VALID, reasons  # nothing priced to validate

    components = [fares.base_fare, fares.taxes, fares.airport_fees, fares.convenience_fee]
    if any(v is not None and v < 0 for v in [*components, fares.total_fare]):
        return QualityFlag.INVALID, ["NEGATIVE_AMOUNT"]
    if fares.total_fare is not None and fares.total_fare <= 0:
        return QualityFlag.INVALID, ["NON_POSITIVE_TOTAL"]

    if fares.base_fare is None:
        reasons.append("BASE_FARE_MISSING")
    if fares.taxes is None:
        reasons.append("TAXES_MISSING")
    if fares.airport_fees is None:
        reasons.append("AIRPORT_FEES_MISSING")
    if fares.convenience_fee is None:
        reasons.append("CONVENIENCE_FEE_MISSING")

    if fares.base_fare is not None and fares.taxes is not None and fares.total_fare is not None:
        parts = sum((v for v in components if v is not None), Decimal(0))
        if abs(parts - fares.total_fare) > tolerance:
            return QualityFlag.INVALID, [*reasons, "TOTAL_MISMATCH"]
    return QualityFlag.VALID, reasons
