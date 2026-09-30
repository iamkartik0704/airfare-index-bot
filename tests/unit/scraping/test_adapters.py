"""Offline parser tests against saved fixtures (doc 14 "Offline Parser Validation")."""

from __future__ import annotations

from datetime import date
from urllib.parse import parse_qs, urlsplit

import pytest

from packages.config.reference import ReferenceData
from packages.domain.enums import FetchMode
from packages.domain.models.job import ScrapeContext
from packages.scraping.core.exceptions import ParseError
from packages.scraping.sources.airlines.indigo import IndigoAdapter
from packages.scraping.sources.registry import ADAPTERS, build_adapter, is_runnable
from packages.scraping.sources.simulated import SimulatedAirlineAdapter, SimulatedOtaAdapter
from packages.scraping.sources.simulated.fetcher import SimulatedFetcher
from tests.helpers import load_fixture, make_response


def ctx(source: str, origin: str = "DEL", dest: str = "BOM") -> ScrapeContext:
    return ScrapeContext(
        source_id=source,
        origin=origin,
        destination=dest,
        travel_date=date(2026, 10, 7),
        purchase_window=7,
        observation_date=date(2026, 9, 30),
    )


class TestIndigoAdapter:
    def test_builds_one_xhr_capture_request(self, reference: ReferenceData) -> None:
        adapter = IndigoAdapter(reference.source("indigo"))
        [request] = adapter.build_requests(ctx("indigo"))
        query = parse_qs(urlsplit(request.url).query)
        assert request.url.startswith("https://www.goindigo.in/")
        assert query["origin"] == ["DEL"] and query["departureDate"] == ["2026-10-07"]
        assert request.capture_xhr == IndigoAdapter.XHR_PATTERN

    def test_parses_fixture_breakdown_sold_out_and_connections(self, reference: ReferenceData) -> None:
        adapter = IndigoAdapter(reference.source("indigo"))
        body = load_fixture("json", "indigo", "availability_DEL_BOM_2026-10-07.json")
        quotes = adapter.parse(make_response(body, content_type="application/json", mode=FetchMode.XHR), ctx("indigo"))
        assert len(quotes) == 5
        saver = quotes[0]
        assert (saver.carrier, saver.flight_number, saver.fare_class) == ("6E", "6E2134", "Saver")
        assert saver.base_fare == "4617.00"
        assert saver.taxes == "257.00"  # K3 GST only
        assert saver.airport_fees == "389.00"  # UDF + ASF + PSF
        assert saver.total_fare == "5263.00"
        assert saver.seats_left == "4" and saver.availability == "AVAILABLE"
        sold_out = quotes[2]
        assert sold_out.flight_number == "6E5021" and sold_out.availability == "SOLD_OUT"
        assert sold_out.total_fare is None
        connection = quotes[4]
        assert connection.flight_number == "6E711/6E404" and connection.stops == "1"

    def test_no_flights_returns_empty(self, reference: ReferenceData) -> None:
        adapter = IndigoAdapter(reference.source("indigo"))
        body = load_fixture("json", "indigo", "availability_no_flights.json")
        assert adapter.parse(make_response(body, content_type="application/json"), ctx("indigo")) == []

    def test_changed_schema_raises_parse_error(self, reference: ReferenceData) -> None:
        adapter = IndigoAdapter(reference.source("indigo"))
        body = load_fixture("json", "indigo", "availability_schema_changed.json")
        with pytest.raises(ParseError):
            adapter.parse(make_response(body, content_type="application/json"), ctx("indigo"))

    def test_metadata_describes_policy(self, reference: ReferenceData) -> None:
        meta = IndigoAdapter(reference.source("indigo")).metadata()
        assert meta.rate_limit_rpm == 6 and meta.crawl_delay_s == 10
        assert meta.purchase_windows == (1, 7, 15, 30, 45)
        assert "xhr_json" in meta.capabilities


class TestSimulatedSource:
    async def test_simulated_round_trip_is_deterministic(self, reference: ReferenceData) -> None:
        adapter = SimulatedAirlineAdapter(reference.source("simulated"))
        [request] = adapter.build_requests(ctx("simulated"))
        first = await SimulatedFetcher(transient_failure_rate=0).fetch(request)
        second = await SimulatedFetcher(transient_failure_rate=0).fetch(request)
        assert first.status == 200
        assert first.body == second.body
        quotes = adapter.parse(first, ctx("simulated"))
        assert quotes and all(q.currency == "INR" for q in quotes)
        assert any(q.total_fare and q.total_fare.startswith("₹") for q in quotes)

    async def test_ota_channel_adds_convenience_fee(self, reference: ReferenceData) -> None:
        fetcher = SimulatedFetcher(transient_failure_rate=0)
        direct = SimulatedAirlineAdapter(reference.source("simulated"))
        ota = SimulatedOtaAdapter(reference.source("simulated_ota"))
        d_resp = await fetcher.fetch(direct.build_requests(ctx("simulated"))[0])
        o_resp = await fetcher.fetch(ota.build_requests(ctx("simulated_ota"))[0])
        d_fees = {q.convenience_fee for q in direct.parse(d_resp, ctx("simulated")) if q.total_fare}
        o_fees = {q.convenience_fee for q in ota.parse(o_resp, ctx("simulated_ota")) if q.total_fare}
        assert d_fees == {"₹0"}
        assert "₹0" not in o_fees

    async def test_transient_failure_happens_once_per_url(self, reference: ReferenceData) -> None:
        fetcher = SimulatedFetcher(transient_failure_rate=1.0)
        request = SimulatedAirlineAdapter(reference.source("simulated")).build_requests(ctx("simulated"))[0]
        assert (await fetcher.fetch(request)).status == 503
        assert (await fetcher.fetch(request)).status == 200

    def test_wrong_search_in_response_is_a_parse_error(self, reference: ReferenceData) -> None:
        adapter = SimulatedAirlineAdapter(reference.source("simulated"))
        body = {"search": {"origin": "BLR", "destination": "HYD"}, "results": []}
        with pytest.raises(ParseError):
            adapter.parse(make_response(body), ctx("simulated"))


class TestRegistry:
    def test_every_registered_adapter_has_a_source_definition(self, reference: ReferenceData) -> None:
        for source_id in ADAPTERS:
            assert build_adapter(reference.source(source_id)).source_id == source_id

    def test_live_sources_are_not_runnable_until_reviewed(self, reference, settings) -> None:  # type: ignore[no-untyped-def]
        assert not is_runnable(reference.source("indigo"), settings)  # enabled: false, no ToS review
        assert is_runnable(reference.source("simulated"), settings)
