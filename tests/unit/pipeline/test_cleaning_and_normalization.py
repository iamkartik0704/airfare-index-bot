from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal

import pytest

from packages.config.reference import ReferenceData
from packages.data_pipeline.cleaning.cleaner import (
    normalize_flight_number,
    parse_departure,
    parse_first_int,
    parse_money,
    parse_stops,
)
from packages.data_pipeline.deduplication.deduper import (
    CanonicalCandidate,
    choose_canonical,
    dedup_key,
    group_key,
)
from packages.data_pipeline.evidence import EvidenceStore
from packages.data_pipeline.exceptions import CleaningError, NormalizationError
from packages.data_pipeline.normalization.normalizer import Normalizer, RawContext
from packages.data_pipeline.validation.outliers import detect_outliers, modified_z_scores
from packages.data_pipeline.validation.rules import validate_fares
from packages.domain.enums import AvailabilityStatus, Cabin, QualityFlag
from packages.domain.exceptions import PersistenceError
from packages.domain.models.quote import FareBreakdown, RawFareQuote


class TestParseMoney:
    @pytest.mark.parametrize(
        ("text", "expected"),
        [
            ("₹1,200.50", "1200.50"),
            ("₹ 5,400", "5400.00"),
            ("Rs. 5400/-", "5400.00"),
            ("INR 1,05,000", "105000.00"),  # Indian lakh grouping
            ("1.000,50", "1000.50"),  # European decimal comma
            ("4617.0", "4617.00"),
            ("Free", "0.00"),
            ("+ ₹48", "48.00"),
            ("+ ₹349 convenience fee", "349.00"),
            ("Rs. 5,310 per adult", "5310.00"),
        ],
    )
    def test_amounts(self, text: str, expected: str) -> None:
        assert parse_money(text) == Decimal(expected)

    @pytest.mark.parametrize("text", [None, "", "—", "N/A"])
    def test_not_displayed_is_none(self, text: str | None) -> None:
        assert parse_money(text) is None

    @pytest.mark.parametrize("text", ["invalid", "$100", "12a4", "₹4,999 or ₹5,499", "Sold out"])
    def test_garbage_raises_instead_of_silent_zero(self, text: str) -> None:
        with pytest.raises(CleaningError):
            parse_money(text)


def test_small_text_parsers() -> None:
    assert parse_first_int("4 seats left") == 4
    assert parse_first_int("Few seats") is None
    assert parse_stops("Non-stop") == 0 and parse_stops("1 stop") == 1
    assert parse_departure("06:05", date(2026, 10, 7)) == datetime(2026, 10, 7, 6, 5)
    assert parse_departure("2026-10-07T21:15:00", date(2026, 10, 7)) == datetime(2026, 10, 7, 21, 15)
    with pytest.raises(CleaningError):
        parse_departure("sometime", date(2026, 10, 7))
    # Formerly a fuzzy string match; now a canonical form makes the variants equal.
    assert normalize_flight_number("AI 101") == normalize_flight_number("AI-101") == "AI101"
    assert normalize_flight_number("6E 711 / 6E 404") == "6E711/6E404"


class TestValidationRules:
    def test_consistent_breakdown_is_valid(self) -> None:
        fares = FareBreakdown(
            base_fare=Decimal(4617), taxes=Decimal(257), airport_fees=Decimal(389),
            convenience_fee=Decimal(0), total_fare=Decimal(5263),
        )
        assert validate_fares(fares, AvailabilityStatus.AVAILABLE, Decimal(2)) == (QualityFlag.VALID, [])

    def test_mismatched_total_is_invalid(self) -> None:
        fares = FareBreakdown(base_fare=Decimal(4000), taxes=Decimal(200), total_fare=Decimal(9000))
        flag, reasons = validate_fares(fares, AvailabilityStatus.AVAILABLE, Decimal(2))
        assert flag is QualityFlag.INVALID and "TOTAL_MISMATCH" in reasons

    def test_total_only_is_valid_with_missing_component_reasons(self) -> None:
        flag, reasons = validate_fares(
            FareBreakdown(total_fare=Decimal(5000)), AvailabilityStatus.AVAILABLE, Decimal(2)
        )
        assert flag is QualityFlag.VALID
        assert {"BASE_FARE_MISSING", "TAXES_MISSING"} <= set(reasons)

    def test_sold_out_needs_no_price(self) -> None:
        assert validate_fares(FareBreakdown(), AvailabilityStatus.SOLD_OUT, Decimal(2))[0] is QualityFlag.VALID


RAW_CTX = RawContext(
    source_id="simulated_ota",
    origin="DEL",
    destination="BOM",
    travel_date=date(2026, 10, 7),
    purchase_window=7,
    observation_date=date(2026, 9, 30),
    observed_at=datetime(2026, 9, 30, 1, 5, tzinfo=UTC),
    is_synthetic=True,
)


class TestNormalizer:
    def _normalizer(self, reference: ReferenceData) -> Normalizer:
        return Normalizer(reference, total_tolerance=Decimal(2))

    def test_ota_card_to_canonical_quote(self, reference: ReferenceData) -> None:
        raw = RawFareQuote(
            carrier="IndiGo", flight_number="6E 2134", fare_class="Flexi Plus",
            departure_time="06:05", stops="Non-stop", base_fare="₹4,617", taxes="₹257",
            airport_fees="₹389", convenience_fee="₹349", total_fare="₹5,612",
            seats_left="4 seats left", availability="AVAILABLE",
        )
        quote = self._normalizer(reference).normalize(raw, RAW_CTX)
        assert (quote.carrier, quote.flight_number) == ("6E", "6E2134")
        assert quote.fare_class == "ECONOMY_FLEX" and quote.cabin is Cabin.ECONOMY
        assert quote.fare_family == "Flexi Plus"
        assert quote.fares.total_fare == Decimal("5612.00")
        assert quote.advance_purchase_days == 7 and quote.seats_left == 4 and quote.stops == 0
        assert quote.departure_at is not None and quote.departure_at.utcoffset().total_seconds() == 19800
        assert quote.quality_flag is QualityFlag.VALID and quote.is_synthetic

    def test_carrier_from_flight_prefix_when_name_missing(self, reference: ReferenceData) -> None:
        raw = RawFareQuote(flight_number="AI 5395", total_fare="₹6,624")
        assert self._normalizer(reference).normalize(raw, RAW_CTX).carrier == "AI"

    @pytest.mark.parametrize(
        "raw",
        [
            RawFareQuote(carrier="Vistara Blue", flight_number="ZZ 12", total_fare="₹1"),
            RawFareQuote(carrier="IndiGo", total_fare="₹5,000"),
            RawFareQuote(carrier="IndiGo", flight_number="6E1", availability="AVAILABLE"),
            RawFareQuote(carrier="IndiGo", flight_number="6E1", total_fare="?", availability="AVAILABLE"),
            RawFareQuote(carrier="IndiGo", flight_number="6E1", availability="waitlisted"),
        ],
    )
    def test_unrepresentable_records_raise(self, reference: ReferenceData, raw: RawFareQuote) -> None:
        with pytest.raises(NormalizationError):
            self._normalizer(reference).normalize(raw, RAW_CTX)

    def test_unknown_fare_family_falls_back_with_reason(self, reference: ReferenceData) -> None:
        raw = RawFareQuote(carrier="SpiceJet", flight_number="SG 8", fare_class="Mystery Box", total_fare="₹4,000")
        quote = self._normalizer(reference).normalize(raw, RAW_CTX)
        assert quote.fare_class == "ECONOMY_STANDARD"
        assert "FARE_CLASS_UNMAPPED" in quote.quality_reasons

    def test_sold_out_quote_has_no_total(self, reference: ReferenceData) -> None:
        raw = RawFareQuote(carrier="IndiGo", flight_number="6E 5021", availability="SOLD_OUT")
        quote = self._normalizer(reference).normalize(raw, RAW_CTX)
        assert quote.availability_status is AvailabilityStatus.SOLD_OUT
        assert quote.fares.total_fare is None


class TestOutliers:
    def test_mad_flags_the_garbled_price(self) -> None:
        totals = [Decimal(x) for x in (5000, 5100, 5200, 4950, 5050, 52000)]
        verdicts = detect_outliers(
            totals, threshold=3.5, min_group_size=5, floor=Decimal(500), ceiling=Decimal(200000)
        )
        assert verdicts == [None, None, None, None, None, "MAD_OUTLIER"]

    def test_bounds_apply_even_to_small_groups(self) -> None:
        verdicts = detect_outliers(
            [Decimal(100), Decimal(5000)], threshold=3.5, min_group_size=5,
            floor=Decimal(500), ceiling=Decimal(200000),
        )
        assert verdicts == ["BELOW_FARE_FLOOR", None]

    def test_identical_values_have_no_outliers(self) -> None:
        assert modified_z_scores([Decimal(5)] * 6) == [Decimal(0)] * 6


class TestDeduplication:
    def test_keys_are_stable_and_scoped(self) -> None:
        d = date(2026, 10, 7), date(2026, 9, 30)
        a = dedup_key("indigo", "6E", "6E2134", "Saver", *d)
        assert a == dedup_key("indigo", "6E", "6E2134", " saver ", *d)
        assert a != dedup_key("makemytrip", "6E", "6E2134", "Saver", *d)
        assert group_key("6E", "6E2134", "ECONOMY_SAVER", *d) == group_key("6E", "6E2134", "ECONOMY_SAVER", *d)

    def test_canonical_prefers_usable_then_direct_then_latest(self) -> None:
        t0 = datetime(2026, 9, 30, 1, tzinfo=UTC)
        t1 = datetime(2026, 9, 30, 2, tzinfo=UTC)
        ota = CanonicalCandidate(1, QualityFlag.VALID, AvailabilityStatus.AVAILABLE, 5, t1)
        direct = CanonicalCandidate(2, QualityFlag.VALID, AvailabilityStatus.AVAILABLE, 1, t0)
        direct_sold = CanonicalCandidate(3, QualityFlag.VALID, AvailabilityStatus.SOLD_OUT, 1, t1)
        dup = CanonicalCandidate(4, QualityFlag.DUPLICATE, AvailabilityStatus.AVAILABLE, 0, t1)
        assert choose_canonical([ota, direct, dup]) == 2
        assert choose_canonical([ota, direct_sold]) == 1
        assert choose_canonical([dup]) is None


class TestEvidenceStore:
    def test_content_addressed_round_trip(self, tmp_path) -> None:  # type: ignore[no-untyped-def]
        store = EvidenceStore(tmp_path)
        sha, uri = store.put(b'{"a":1}')
        assert store.put(b'{"a":1}') == (sha, uri)
        assert uri.startswith("evidence://") and store.get(uri) == b'{"a":1}'

    def test_tampered_body_fails_integrity_check(self, tmp_path) -> None:  # type: ignore[no-untyped-def]
        import gzip

        store = EvidenceStore(tmp_path)
        sha, uri = store.put(b"original")
        path = tmp_path / sha[:2] / sha[2:4] / f"{sha}.gz"
        path.write_bytes(gzip.compress(b"tampered"))
        with pytest.raises(PersistenceError):
            store.get(uri)
