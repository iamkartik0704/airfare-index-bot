"""The scrape executor: governance → rate limit → fetch → classify → parse.

``ScrapeExecutor.execute(adapter, context)`` runs one scrape task and always
returns a ``ScrapeOutcome``. Every response that was received is included —
successful pages, block pages and pages the parser choked on — so the caller
can store it as evidence before deciding the job's fate (docs 02 §4, 07).
Typed errors are captured on the outcome, never swallowed.

Per request:

1. ``RobotsGate`` — disallowed URLs are never requested (doc 15).
2. ``DomainRateLimiter`` — spacing = max(60/rpm, Crawl-delay) per host.
3. ``ConcurrencyLimiter`` — at most ``max_concurrency`` in flight per source.
4. ``RetryPolicy`` — exponential backoff for network errors, 5xx and 429
   (429 also pauses the whole host for ``Retry-After``).
5. Block detection — challenge/CAPTCHA/403 stops the task; never bypassed.
6. ``adapter.parse`` — structural failures become ``ParseError``.
"""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from urllib.parse import urljoin, urlsplit

from packages.config.settings import ScrapingSettings
from packages.domain.models.job import ScrapeContext
from packages.domain.models.quote import RawFareQuote
from packages.domain.models.source import HealthCheckResult
from packages.observability.logging import get_logger
from packages.observability.metrics import metrics
from packages.scraping.core.exceptions import (
    ParseError,
    RobotsDisallowedError,
    ScrapingError,
    SourceBlockedError,
)
from packages.scraping.core.fetchers.base import BaseFetcher, FetchRequest, FetchResponse
from packages.scraping.core.governance.blocking import raise_for_response
from packages.scraping.core.governance.robots import RobotsGate
from packages.scraping.core.rate_limit.limiter import ConcurrencyLimiter, DomainRateLimiter
from packages.scraping.core.resilience.retry import RetryPolicy
from packages.scraping.fetchers import FetcherFactory
from packages.scraping.sources.base import BaseSourceAdapter

log = get_logger("safar.scraping")

# Structural bugs an adapter can hit on an unexpected payload; converted to ParseError.
_PARSER_BUG_TYPES = (KeyError, IndexError, TypeError, ValueError, AttributeError)


@dataclass(frozen=True)
class ParsedQuote:
    response_index: int
    record_index: int
    quote: RawFareQuote


@dataclass
class ScrapeOutcome:
    source_id: str
    responses: list[FetchResponse] = field(default_factory=list)
    quotes: list[ParsedQuote] = field(default_factory=list)
    error: ScrapingError | None = None
    requests_sent: int = 0
    retries: int = 0

    @property
    def succeeded(self) -> bool:
        return self.error is None


class GovernedFetcher(BaseFetcher):
    """Wraps a transport with robots, rate-limit and concurrency governance."""

    def __init__(
        self,
        inner: BaseFetcher,
        adapter: BaseSourceAdapter,
        robots: RobotsGate,
        limiter: DomainRateLimiter,
        concurrency: ConcurrencyLimiter,
    ) -> None:
        self.mode = inner.mode
        self._inner = inner
        self._source = adapter.definition
        self._robots = robots
        self._limiter = limiter
        self._concurrency = concurrency

    async def fetch(self, request: FetchRequest) -> FetchResponse:
        decision = await self._robots.check(request.url)
        if not decision.allowed:
            metrics.ROBOTS_DENIED.labels(self._source.id).inc()
            raise RobotsDisallowedError(decision.reason, source=self._source.id, url=request.url)
        if request.capture_xhr and request.capture_xhr.startswith("/"):
            # The page's own API call is captured, not requested — but we still only
            # read endpoints the site allows automated agents to use.
            xhr_url = urljoin(request.url, request.capture_xhr)
            xhr_decision = await self._robots.check(xhr_url)
            if not xhr_decision.allowed:
                metrics.ROBOTS_DENIED.labels(self._source.id).inc()
                raise RobotsDisallowedError(
                    f"captured endpoint {xhr_decision.reason}", source=self._source.id, url=xhr_url
                )
        host = urlsplit(request.url).netloc.lower()
        self._limiter.configure(
            host,
            requests_per_minute=self._source.rate_limit_rpm,
            crawl_delay_s=max(self._source.crawl_delay_s, decision.crawl_delay_s or 0.0),
        )
        async with self._concurrency.slot(self._source.id, self._source.max_concurrency):
            await self._limiter.acquire(host)
            response = await self._inner.fetch(request)
        metrics.SCRAPE_REQUESTS.labels(self._source.id, str(response.status)).inc()
        metrics.SCRAPE_LATENCY.labels(self._source.id, response.fetch_mode.value).observe(
            response.elapsed_ms / 1000
        )
        if response.status == 429:
            retry_after = 60.0
            for key, value in response.headers.items():
                if key.lower() == "retry-after" and value.isdigit():
                    retry_after = float(value)
            self._limiter.pause(host, retry_after)
        return response


class ScrapeExecutor:
    def __init__(
        self,
        fetchers: FetcherFactory,
        settings: ScrapingSettings,
        *,
        robots: RobotsGate | None = None,
        limiter: DomainRateLimiter | None = None,
        concurrency: ConcurrencyLimiter | None = None,
        retry: RetryPolicy | None = None,
        sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
    ) -> None:
        self._fetchers = fetchers
        self._robots = robots or RobotsGate(
            agent_token=settings.robots_user_agent_token,
            user_agent=settings.user_agent,
            fail_closed=settings.robots_fail_closed,
            ttl_s=settings.robots_cache_ttl_s,
        )
        self._limiter = limiter or DomainRateLimiter()
        self._concurrency = concurrency or ConcurrencyLimiter()
        self._retry = retry or RetryPolicy(
            max_attempts=settings.max_retries,
            base_delay_s=settings.backoff_base_s,
            max_delay_s=settings.backoff_max_s,
        )
        self._sleep = sleep

    def governed(self, adapter: BaseSourceAdapter) -> GovernedFetcher:
        inner = self._fetchers.get(adapter.definition.fetch_mode)
        return GovernedFetcher(inner, adapter, self._robots, self._limiter, self._concurrency)

    async def execute(self, adapter: BaseSourceAdapter, context: ScrapeContext) -> ScrapeOutcome:
        outcome = ScrapeOutcome(source_id=adapter.source_id)
        fetcher = self.governed(adapter)
        try:
            requests = adapter.build_requests(context)
        except _PARSER_BUG_TYPES as exc:
            outcome.error = ParseError(f"could not build requests: {exc}", source=adapter.source_id)
            return outcome

        for request in requests:
            response = await self._fetch_with_retry(fetcher, adapter, request, outcome)
            if response is None:
                return outcome
            outcome.responses.append(response)
            response_index = len(outcome.responses) - 1
            try:
                raise_for_response(
                    response, source_id=adapter.source_id, extra_markers=adapter.block_markers
                )
            except SourceBlockedError as exc:
                metrics.SCRAPE_BLOCKS.labels(adapter.source_id).inc()
                log.warning("scrape.blocked", reason=exc.message, url=response.url)
                outcome.error = exc
                return outcome
            except ScrapingError as exc:  # non-retryable 4xx after retries were exhausted
                outcome.error = exc
                return outcome
            try:
                quotes = adapter.parse(response, context)
            except ParseError as exc:
                outcome.error = exc
            except _PARSER_BUG_TYPES as exc:
                outcome.error = ParseError(
                    f"unexpected payload structure: {exc.__class__.__name__}: {exc}",
                    source=adapter.source_id,
                    url=response.url,
                )
            if outcome.error is not None:
                metrics.PARSER_FAILURES.labels(adapter.source_id).inc()
                log.error("scrape.parse_failed", error=str(outcome.error), url=response.url)
                return outcome
            outcome.quotes.extend(ParsedQuote(response_index, i, q) for i, q in enumerate(quotes))
        metrics.QUOTES_COLLECTED.labels(adapter.source_id).inc(len(outcome.quotes))
        return outcome

    async def _fetch_with_retry(
        self,
        fetcher: GovernedFetcher,
        adapter: BaseSourceAdapter,
        request: FetchRequest,
        outcome: ScrapeOutcome,
    ) -> FetchResponse | None:
        async def attempt() -> FetchResponse:
            outcome.requests_sent += 1
            response = await fetcher.fetch(request)
            if response.status == 429 or response.status >= 500:
                # Retryable statuses are raised here so RetryPolicy backs off.
                raise_for_response(response, source_id=adapter.source_id)
            return response

        def on_retry(n: int, exc: BaseException, delay: float) -> None:
            outcome.retries += 1
            log.info("scrape.retry", attempt=n, delay_s=round(delay, 2), error=str(exc))

        try:
            return await self._retry.run(attempt, sleep=self._sleep, on_retry=on_retry)
        except ScrapingError as exc:
            outcome.error = exc
            return None

    async def health_check(self, adapter: BaseSourceAdapter) -> HealthCheckResult:
        return await adapter.health_check(self.governed(adapter))
