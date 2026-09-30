"""Stage 8 adapters: offline fixture parsing, normalization, and robots governance."""

from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal

import pytest

from packages.config.reference import ReferenceData
from packages.config.settings import Settings
from packages.data_pipeline.exceptions import NormalizationError
from packages.data_pipeline.normalization.normalizer import Normalizer, RawContext
from packages.domain.enums import AvailabilityStatus, QualityFlag
from packages.domain.models.job import ScrapeContext
from packages.scraping.core.exceptions import ParseError, RobotsDisallowedError
from packages.scraping.core.rate_limit.limiter import DomainRateLimiter
from packages.scraping.core.resilience.retry import RetryPolicy
from packages.scraping.engine import ScrapeExecutor
from packages.scraping.fetchers import FetcherFactory
from packages.scraping.sources.common.dom_cards import DomCardAdapter
from packages.scraping.sources.registry import build_adapter
from tests.helpers import ScriptedFetcher, load_fixture, make_response, no_sleep, robots_gate

CTX = ScrapeContext(
    source_id="x",
    origin="DEL",
    destination="BOM",
    travel_date=date(2026, 10, 7),
    purchase_window=7,
    observation_date=date(2026, 9, 30),
)

# source, fixture path, expected quote count, expected sold-out count, expected carriers
CASES = [
    ("air_india", ("json", "air_india", "air_bounds_DEL_BOM_2026-10-07.json"), 4, 2, {"AI"}),
    ("air_india_express", ("json", "air_india_express", "availability_DEL_BOM_2026-10-07.json"), 1, 0, {"IX"}),
    ("akasa", ("json", "akasa", "availability_DEL_BOM_2026-10-07.json"), 1, 0, {"QP"}),
    ("spicejet", ("html", "spicejet", "results_DEL_BOM.html"), 3, 1, {"SG"}),
    ("makemytrip", ("html", "makemytrip", "results_DEL_BOM.html"), 3, 1, {"6E", "AI", "QP"}),
    ("yatra", ("html", "yatra", "results_DEL_BOM.html"), 2, 0, {"SG", "IX"}),
    ("easemytrip", ("html", "easemytrip", "results_DEL_BOM.html"), 2, 1, {"6E"}),
    ("cleartrip", ("html", "cleartrip", "results_DEL_BOM.html"), 2, 0, {"AI", "6E"}),
    ("ixigo", ("html", "ixigo", "results_DEL_BOM.html"), 1, 0, {"QP"}),
]


def _response(parts: tuple[str, ...]):  # type: ignore[no-untyped-def]
    body = load_fixture(*parts)
    ctype = "application/json" if parts[0] == "json" else "text/html; charset=utf-8"
    return make_response(body, content_type=ctype)


@pytest.mark.parametrize(("source", "fixture", "count", "sold_out", "carriers"), CASES)
def test_fixture_parses_and_normalizes(
    reference: ReferenceData,
    source: str,
    fixture: tuple[str, ...],
    count: int,
    sold_out: int,
    carriers: set[str],
) -> None:
    adapter = build_adapter(reference.source(source))
    [request] = adapter.build_requests(CTX)
    assert request.url.startswith(reference.source(source).base_url)
    raws = adapter.parse(_response(fixture), CTX)
    assert len(raws) == count
    normalizer = Normalizer(reference, total_tolerance=Decimal(2))
    ctx = RawContext(
        source_id=source, origin="DEL", destination="BOM", travel_date=CTX.travel_date,
        purchase_window=7, observation_date=CTX.observation_date,
        observed_at=datetime(2026, 9, 30, 1, tzinfo=UTC), is_synthetic=False,
    )
    quotes = [normalizer.normalize(r, ctx) for r in raws]
    assert {q.carrier for q in quotes} == carriers
    assert sum(q.availability_status is AvailabilityStatus.SOLD_OUT for q in quotes) == sold_out
    for q in quotes:
        assert q.quality_flag is not QualityFlag.INVALID
        if q.availability_status is AvailabilityStatus.AVAILABLE:
            assert q.fares.total_fare is not None and q.fares.total_fare > 1000


def test_ota_convenience_fee_and_connections(reference: ReferenceData) -> None:
    normalizer = Normalizer(reference, total_tolerance=Decimal(2))
    ctx = RawContext("cleartrip", "DEL", "BOM", CTX.travel_date, 7, CTX.observation_date,
                     datetime(2026, 9, 30, tzinfo=UTC), False)
    raws = build_adapter(reference.source("cleartrip")).parse(_response(CASES[7][1]), CTX)
    direct, connection = (normalizer.normalize(r, ctx) for r in raws)
    assert direct.fares.convenience_fee == Decimal("399.00")
    assert connection.flight_number == "6E711/6E404" and connection.stops == 1


def test_air_india_reports_airport_fees_as_not_displayed(reference: ReferenceData) -> None:
    raws = build_adapter(reference.source("air_india")).parse(_response(CASES[0][1]), CTX)
    value = raws[0]
    assert (value.base_fare, value.taxes, value.total_fare) == ("5520", "890", "6410")
    assert value.airport_fees is None and value.fare_class == "Economy Value"


@pytest.mark.parametrize("source", ["spicejet", "makemytrip", "yatra", "easemytrip", "cleartrip", "ixigo"])
def test_dom_layout_change_raises_but_no_results_page_is_empty(reference: ReferenceData, source: str) -> None:
    adapter = build_adapter(reference.source(source))
    assert isinstance(adapter, DomCardAdapter)
    with pytest.raises(ParseError):
        adapter.parse(make_response("<html><body><div class='redesigned'></div></body></html>"), CTX)
    marker = adapter.SPEC.no_results[0]
    if marker.startswith("."):
        html = f"<div class='{marker[1:]}'>No flights</div>"
    else:  # [data-...='...'] attribute selector
        attr, value = marker.strip("[]").split("=")
        html = f"<div {attr}={value}>No flights</div>"
    assert adapter.parse(make_response(f"<html><body>{html}</body></html>"), CTX) == []


def test_card_without_flight_number_is_a_parse_error(reference: ReferenceData) -> None:
    adapter = build_adapter(reference.source("makemytrip"))
    with pytest.raises(ParseError):
        adapter.parse(make_response("<div class='listingCard'><p class='fontSize18'>₹5</p></div>"), CTX)


def test_unknown_airline_on_ota_is_rejected_by_normalization(reference: ReferenceData) -> None:
    normalizer = Normalizer(reference, total_tolerance=Decimal(2))
    raws = build_adapter(reference.source("yatra")).parse(
        make_response(
            "<div class='flightItem'><span class='airline-name'>Star Air</span>"
            "<span class='flight-no'>S5-101</span><span class='fare-price'>Rs. 3,000</span></div>"
        ),
        CTX,
    )
    ctx = RawContext("yatra", "DEL", "BOM", CTX.travel_date, 7, CTX.observation_date,
                     datetime(2026, 9, 30, tzinfo=UTC), False)
    with pytest.raises(NormalizationError):
        normalizer.normalize(raws[0], ctx)


# robots.txt rules as published on 2026-09-30 (see packages/config/reference/sources.yaml).
ROBOTS_SNAPSHOTS = {
    "ixigo": "User-agent: *\nDisallow: /search/result/\nDisallow: /flights/search\nDisallow: /api/\ncrawl-delay: 10\n",
    "easemytrip": "User-Agent: *\nDisallow: /cheap_flights/\nDisallow: /flight-search/listing*\n",
    "air_india_express": "User-agent: *\nDisallow: /flight-availability\n",
}


@pytest.mark.parametrize("source", sorted(ROBOTS_SNAPSHOTS))
async def test_published_robots_rules_block_the_adapter(
    settings: Settings, reference: ReferenceData, source: str
) -> None:
    fetcher = ScriptedFetcher([make_response("<html></html>")])
    factory = FetcherFactory(settings.scraping)
    factory.register("browser", fetcher)
    executor = ScrapeExecutor(
        factory, settings.scraping, robots=robots_gate(ROBOTS_SNAPSHOTS[source]),
        limiter=DomainRateLimiter(sleep=no_sleep), retry=RetryPolicy(max_attempts=1), sleep=no_sleep,
    )
    outcome = await executor.execute(build_adapter(reference.source(source)), CTX)
    assert isinstance(outcome.error, RobotsDisallowedError)
    assert fetcher.requests == []  # nothing was sent


async def test_captured_xhr_endpoint_must_also_be_allowed(settings: Settings, reference: ReferenceData) -> None:
    fetcher = ScriptedFetcher([make_response({"data": {"trips": []}})])
    factory = FetcherFactory(settings.scraping)
    factory.register("browser", fetcher)
    executor = ScrapeExecutor(
        factory, settings.scraping, robots=robots_gate("User-agent: *\nDisallow: /v1/availability\n"),
        limiter=DomainRateLimiter(sleep=no_sleep), sleep=no_sleep,
    )
    outcome = await executor.execute(build_adapter(reference.source("indigo")), CTX)
    assert isinstance(outcome.error, RobotsDisallowedError)
    assert "captured endpoint" in outcome.error.message and fetcher.requests == []
