from __future__ import annotations

from datetime import date

import httpx
import pytest

from packages.config.reference import ReferenceData
from packages.config.settings import Settings
from packages.domain.enums import FetchMode
from packages.domain.models.job import ScrapeContext
from packages.domain.models.quote import RawFareQuote
from packages.scraping.core.exceptions import (
    FetchTimeoutError,
    NetworkError,
    ParseError,
    RateLimitedError,
    RobotsDisallowedError,
    SourceBlockedError,
)
from packages.scraping.core.fetchers.base import FetchRequest, FetchResponse
from packages.scraping.core.fetchers.http import HttpFetcher
from packages.scraping.core.rate_limit.limiter import DomainRateLimiter
from packages.scraping.core.resilience.retry import RetryPolicy
from packages.scraping.core.session.session_manager import SessionManager
from packages.scraping.engine import ScrapeExecutor
from packages.scraping.fetchers import FetcherFactory
from packages.scraping.sources.base import BaseSourceAdapter
from tests.helpers import ScriptedFetcher, make_response, no_sleep, robots_gate

UA = "MoSPI-SAFAR-Bot/1.0"


class TestHttpFetcher:
    async def test_returns_unified_response_and_keeps_cookies(self) -> None:
        seen: list[httpx.Request] = []

        def handler(request: httpx.Request) -> httpx.Response:
            seen.append(request)
            return httpx.Response(
                200,
                json={"success": True},
                headers={"set-cookie": "sid=abc; Path=/"},
            )

        session = SessionManager(UA)
        fetcher = HttpFetcher(session, transport=httpx.MockTransport(handler))
        resp = await fetcher.fetch(FetchRequest(url="https://api.example.test/x", params={"a": "1"}))
        assert resp.status == 200
        assert resp.json() == {"success": True}
        assert resp.fetch_mode is FetchMode.HTTP
        assert "set-cookie" not in {k.lower() for k in resp.headers}
        assert seen[0].headers["user-agent"] == UA
        await fetcher.fetch(FetchRequest(url="https://api.example.test/y"))
        assert seen[1].headers["cookie"] == "sid=abc"
        await fetcher.aclose()

    async def test_transport_errors_are_typed(self) -> None:
        def timeout(request: httpx.Request) -> httpx.Response:
            raise httpx.ReadTimeout("slow", request=request)

        def reset(request: httpx.Request) -> httpx.Response:
            raise httpx.ConnectError("reset", request=request)

        session = SessionManager(UA)
        with pytest.raises(FetchTimeoutError):
            await HttpFetcher(session, transport=httpx.MockTransport(timeout)).fetch(
                FetchRequest(url="https://h.test/")
            )
        with pytest.raises(NetworkError):
            await HttpFetcher(session, transport=httpx.MockTransport(reset)).fetch(
                FetchRequest(url="https://h.test/")
            )

    def test_response_helpers(self) -> None:
        resp = make_response("<ul><li class='f'> 6E  201 </li><li class='g'>x</li></ul>")
        sel = resp.selector()
        assert sel.text(".missing", ".f") == "6E 201"
        assert [s.text() for s in sel.css(".f", ".g")] == ["6E 201"]
        with pytest.raises(ParseError):
            sel.require_text(".nothing", field_name="fare")
        with pytest.raises(ParseError):
            make_response("not json", content_type="application/json").json()
        assert len(resp.sha256) == 64


class EchoAdapter(BaseSourceAdapter):
    """Minimal adapter: one request, JSON list of fares."""

    source_id = "indigo"
    block_markers = ("indigo-waiting-room",)

    def build_requests(self, context: ScrapeContext) -> list[FetchRequest]:
        return [FetchRequest(url=f"https://www.goindigo.in/s?d={context.travel_date}")]

    def parse(self, response: FetchResponse, context: ScrapeContext) -> list[RawFareQuote]:
        payload = response.json()
        return [RawFareQuote(flight_number=f["no"], total_fare=f["fare"]) for f in payload["fares"]]


CTX = ScrapeContext(
    source_id="indigo",
    origin="DEL",
    destination="BOM",
    travel_date=date(2026, 10, 7),
    purchase_window=7,
    observation_date=date(2026, 9, 30),
)


def _executor(settings: Settings, fetcher: ScriptedFetcher, robots: str | None = None) -> ScrapeExecutor:
    factory = FetcherFactory(settings.scraping)
    factory.register("browser", fetcher)
    return ScrapeExecutor(
        factory,
        settings.scraping,
        robots=robots_gate(robots or "User-agent: *\nAllow: /"),
        limiter=DomainRateLimiter(sleep=no_sleep),
        retry=RetryPolicy(max_attempts=3, base_delay_s=0),
        sleep=no_sleep,
    )


class TestScrapeExecutor:
    async def test_success_collects_quotes_with_positions(
        self, settings: Settings, reference: ReferenceData
    ) -> None:
        fetcher = ScriptedFetcher([make_response({"fares": [{"no": "6E1", "fare": "₹5,000"}]})])
        outcome = await _executor(settings, fetcher).execute(EchoAdapter(reference.source("indigo")), CTX)
        assert outcome.succeeded
        assert [(q.response_index, q.record_index) for q in outcome.quotes] == [(0, 0)]
        assert outcome.quotes[0].quote.total_fare == "₹5,000"

    async def test_retries_5xx_then_succeeds(self, settings: Settings, reference: ReferenceData) -> None:
        fetcher = ScriptedFetcher(
            [make_response("busy", status=503), make_response({"fares": []})]
        )
        outcome = await _executor(settings, fetcher).execute(EchoAdapter(reference.source("indigo")), CTX)
        assert outcome.succeeded
        assert outcome.retries == 1 and outcome.requests_sent == 2

    async def test_429_exhausts_retries_as_rate_limited(
        self, settings: Settings, reference: ReferenceData
    ) -> None:
        fetcher = ScriptedFetcher([make_response("", status=429, headers={"Retry-After": "0"})])
        outcome = await _executor(settings, fetcher).execute(EchoAdapter(reference.source("indigo")), CTX)
        assert isinstance(outcome.error, RateLimitedError)
        assert outcome.requests_sent == 3

    async def test_block_is_recorded_with_evidence_and_not_retried(
        self, settings: Settings, reference: ReferenceData
    ) -> None:
        fetcher = ScriptedFetcher([make_response("<html>indigo-waiting-room</html>")])
        outcome = await _executor(settings, fetcher).execute(EchoAdapter(reference.source("indigo")), CTX)
        assert isinstance(outcome.error, SourceBlockedError)
        assert len(outcome.responses) == 1 and outcome.requests_sent == 1

    async def test_parser_bug_becomes_parse_error_and_keeps_response(
        self, settings: Settings, reference: ReferenceData
    ) -> None:
        fetcher = ScriptedFetcher([make_response({"unexpected": True})])
        outcome = await _executor(settings, fetcher).execute(EchoAdapter(reference.source("indigo")), CTX)
        assert isinstance(outcome.error, ParseError)
        assert len(outcome.responses) == 1 and not outcome.quotes

    async def test_robots_disallow_sends_nothing(self, settings: Settings, reference: ReferenceData) -> None:
        fetcher = ScriptedFetcher([make_response({"fares": []})])
        outcome = await _executor(settings, fetcher, "User-agent: *\nDisallow: /s").execute(
            EchoAdapter(reference.source("indigo")), CTX
        )
        assert isinstance(outcome.error, RobotsDisallowedError)
        assert fetcher.requests == []

    async def test_network_failure_after_retries(self, settings: Settings, reference: ReferenceData) -> None:
        fetcher = ScriptedFetcher([NetworkError("reset")])
        outcome = await _executor(settings, fetcher).execute(EchoAdapter(reference.source("indigo")), CTX)
        assert isinstance(outcome.error, NetworkError)
        assert outcome.requests_sent == 3 and not outcome.responses
