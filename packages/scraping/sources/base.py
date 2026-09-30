"""The ``BaseSourceAdapter`` contract (doc 05).

The rest of SAFAR never sees a selector, a JSON path or a query-string format:
those live only inside an adapter. An adapter

1. declares ``metadata()`` — capabilities, rate limits, purchase windows;
2. turns a ``ScrapeContext`` into ``FetchRequest``s (``build_requests``);
3. turns a ``FetchResponse`` into ``RawFareQuote``s (``parse``), raising
   ``ParseError`` when a mandatory field or structure is missing — never
   silently dropping data or inserting zeros;
4. offers a fast structural ``health_check``.

Adding a source = one adapter module + one ``sources.yaml`` entry + fixtures.
"""

from __future__ import annotations

import abc
import time
from datetime import UTC, datetime
from typing import ClassVar

from packages.config.reference import SourceDef
from packages.config.settings import PURCHASE_WINDOWS
from packages.domain.models.job import ScrapeContext
from packages.domain.models.quote import RawFareQuote
from packages.domain.models.source import HealthCheckResult, SourceMetadata
from packages.scraping.core.exceptions import ScrapingError
from packages.scraping.core.fetchers.base import BaseFetcher, FetchRequest, FetchResponse
from packages.scraping.core.governance.blocking import detect_block


class BaseSourceAdapter(abc.ABC):
    #: Must equal the ``sources.yaml`` id and the adapter's package name.
    source_id: ClassVar[str]
    #: Bump whenever parsing logic changes; stored on every raw quote.
    parser_version: ClassVar[str] = "1"
    capabilities: ClassVar[tuple[str, ...]] = ()
    #: Extra, source-specific challenge markers (added to the global list).
    block_markers: ClassVar[tuple[str, ...]] = ()
    #: Strings the health-check page must contain for the structure to be "as expected".
    health_markers: ClassVar[tuple[str, ...]] = ()

    def __init__(self, definition: SourceDef) -> None:
        if definition.id != self.source_id:
            raise ValueError(f"{type(self).__name__} cannot serve source {definition.id!r}")
        self.definition = definition

    @property
    def parser_name(self) -> str:
        return f"{self.source_id}.{type(self).__name__}"

    def metadata(self) -> SourceMetadata:
        d = self.definition
        return SourceMetadata(
            id=d.id,
            name=d.name,
            kind=d.kind,
            base_url=d.base_url,
            carrier=d.carrier,
            fetch_mode=d.fetch_mode,
            rate_limit_rpm=d.rate_limit_rpm,
            max_concurrency=d.max_concurrency,
            crawl_delay_s=d.crawl_delay_s,
            purchase_windows=PURCHASE_WINDOWS,
            parser_name=self.parser_name,
            parser_version=self.parser_version,
            capabilities=self.capabilities,
            is_synthetic=d.is_synthetic,
        )

    @abc.abstractmethod
    def build_requests(self, context: ScrapeContext) -> list[FetchRequest]:
        """Translate a route/date/window into the request(s) the source needs."""

    @abc.abstractmethod
    def parse(self, response: FetchResponse, context: ScrapeContext) -> list[RawFareQuote]:
        """Extract raw fares. Return ``[]`` only when the source states there are no flights."""

    def health_check_request(self) -> FetchRequest:
        return FetchRequest(url=self.definition.base_url + "/")

    async def health_check(self, fetcher: BaseFetcher) -> HealthCheckResult:
        """Fetch a lightweight page and verify the expected structure markers."""
        started = time.perf_counter()
        checked_at = datetime.now(UTC)
        try:
            response = await fetcher.fetch(self.health_check_request())
        except ScrapingError as exc:
            return HealthCheckResult(
                source_id=self.source_id, ok=False, checked_at=checked_at, detail=str(exc)
            )
        latency = int((time.perf_counter() - started) * 1000)
        verdict = detect_block(response, self.block_markers)
        missing = [m for m in self.health_markers if m not in response.text]
        ok = response.status < 400 and not verdict.blocked and not missing
        if verdict.blocked:
            detail = f"blocked: {verdict.reason}"
        elif missing:
            detail = f"structure changed: missing {missing}"
        else:
            detail = f"HTTP {response.status}"
        return HealthCheckResult(
            source_id=self.source_id,
            ok=ok,
            checked_at=checked_at,
            status_code=response.status,
            latency_ms=latency,
            detail=detail,
        )
