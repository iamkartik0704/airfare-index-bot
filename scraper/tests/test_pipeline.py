"""
Automated tests for the SAFAR pipeline.

    cd scraper && pytest -q

Covers the three things a statistical agency would ask about: that the cleaning
funnel behaves, that outliers are rejected without eating genuine spikes, and
that the index estimator is internally consistent.
"""

from __future__ import annotations

import sys
from datetime import date, timedelta
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from safar.clean import CARRIER_FARE_INDEX, CleanQuote, clean_quotes  # noqa: E402
from safar.collect.base import RobotsGate, TokenBucket, parse_rupees  # noqa: E402
from safar.index import ROUTE_W, backtest, base_snapshot, build_index, monthly_series, route_price  # noqa: E402


def make_quote(**kw) -> "object":
    from safar.collect.base import RawQuote

    base = dict(
        source_id="indigo", carrier="6E", route_id="DEL-BOM", origin="DEL",
        destination="BOM", departure="2026-10-07", lead_time=7, fare_class="VALUE",
        flight_no="6E123", fare_text="₹6,500", tax_text="₹1,240", fee_text="—",
        seats_left=9, refundable=False, baggage_kg=15,
        collected_at="2026-09-30T05:10:00Z",
    )
    base.update(kw)
    return RawQuote(**base)


class TestParsing:
    @pytest.mark.parametrize(
        "text,expected",
        [("₹6,500", 6500.0), ("Rs. 6500", 6500.0), ("INR 6,500.50", 6500.5), ("", 0.0)],
    )
    def test_rupee_parser(self, text, expected):
        assert parse_rupees(text) == expected

    def test_token_bucket_is_never_bursty(self):
        bucket = TokenBucket(per_minute=6, crawl_delay=0, jitter_pct=0)
        assert bucket.interval == pytest.approx(10.0)

    def test_robots_gate_defaults_to_disallow(self):
        gate = RobotsGate()
        gate._parsers["https://example.invalid"] = _DenyingParser()
        assert gate.allowed("https://example.invalid/flight/search") is False


class _DenyingParser:
    def can_fetch(self, *_args, **_kwargs):
        return False

    def crawl_delay(self, *_args, **_kwargs):
        return None


class TestCleaning:
    def test_sold_out_and_duplicate_are_dropped(self):
        raw = [
            make_quote(),
            make_quote(),  # duplicate listing
            make_quote(seats_left=0),  # sold-out stub
        ]
        _, report = clean_quotes(raw)
        assert report["rawCount"] == 3
        assert report["droppedDuplicate"] == 1
        assert report["droppedSoldOut"] == 1

    def test_outlier_glitch_is_rejected(self):
        raw = [make_quote(fare_text=f"₹{6000 + i * 10}") for i in range(20)]
        raw.append(make_quote(fare_text="₹48,000"))  # tariff glitch
        _, report = clean_quotes(raw)
        assert report["droppedOutlier"] == 1
        assert report["keptCount"] == 20

    def test_blocked_carrier_cell_is_imputed_and_flagged(self):
        raw = [make_quote(carrier=c, fare_text="₹6,500") for c in ("6E",)]
        cleaned, report = clean_quotes(raw)
        imputed = [q for q in cleaned if q.imputed]
        assert report["imputedCount"] == len(CARRIER_FARE_INDEX) - 1
        assert all("anti-bot-block" in q.flags for q in imputed)

    def test_decomposition_sums_to_total(self):
        cleaned, _ = clean_quotes([make_quote()])
        q = cleaned[0]
        assert q.base_fare + q.taxes + q.convenience_fee == q.total_fare


class TestIndex:
    def _basket(self, multiplier: float = 1.0) -> list[CleanQuote]:
        rows = []
        for route in ROUTE_W:
            for lead in (1, 7, 15, 30, 45):
                rows.append(
                    CleanQuote(
                        source_id="indigo", carrier="6E", route_id=route, lead_time=lead,
                        fare_class="VALUE", base_fare=6000 * multiplier,
                        taxes=1200 * multiplier, udf=0, convenience_fee=0,
                        total_fare=7200 * multiplier, quality=0.95,
                    )
                )
        return rows

    def test_reference_period_equals_100(self):
        base = base_snapshot(self._basket())
        point = build_index(self._basket(), date(2026, 9, 30), base)
        assert point["value"] == pytest.approx(100.0, abs=0.5)

    def test_uniform_inflation_moves_the_index_one_for_one(self):
        base = base_snapshot(self._basket())
        shocked = build_index(self._basket(1.10), date(2026, 9, 30), base)
        assert shocked["value"] == pytest.approx(110.0, abs=0.5)

    def test_quality_mix_shift_is_divided_out(self):
        base = base_snapshot(self._basket())
        rows = self._basket()
        for q in rows:
            q.quality = 1.10  # travellers moved up a fare class, same price
        shifted = build_index(rows, date(2026, 9, 30), base)
        assert shifted["value"] < 100.5  # no phantom inflation

    def test_lead_time_weights_collapse_windows(self):
        rows = [
            CleanQuote("indigo", "6E", "DEL-BOM", lead, "VALUE", 6000, 1200, 0, 0,
                       7200 if lead != 1 else 14000, 0.95)
            for lead in (1, 7, 15, 30, 45)
        ]
        price, _ = route_price(rows)
        assert 6000 < price < 8000  # T+1 is priced in, but weighted at 8%

    def test_monthly_series_has_mom_and_yoy(self):
        points = [
            {"date": (date(2025, 1, 1) + timedelta(days=i)).isoformat(), "value": 100 + i * 0.05}
            for i in range(800)
        ]
        monthly = monthly_series(points)
        assert len(monthly) >= 26
        assert "change" in monthly[1]
        assert "yoy" in monthly[12]


class TestBacktest:
    def test_identical_series_pass(self):
        points = [
            {"date": (date(2025, 1, 1) + timedelta(days=i * 30)).isoformat(), "value": 100 + i}
            for i in range(12)
        ]
        dgca = {p["date"][:7]: p["value"] for p in points}
        result = backtest(points, dgca)
        assert result["pearson"] == pytest.approx(1.0, abs=0.01)
        assert result["verdict"].startswith("PASS")

    def test_insufficient_overlap_is_reported(self):
        result = backtest([{"date": "2026-01-01", "value": 100}], {"2026-01": 100})
        assert result["verdict"] == "insufficient overlap"
