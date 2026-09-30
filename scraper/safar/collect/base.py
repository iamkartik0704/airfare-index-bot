"""
SAFAR collector base — the contract every source adapter implements.

This is the Python twin of `src/convex/lib/adapters.ts`: the same
`SourceAdapter` interface, the same selectors, the same rate limits, the same
compliance rules. Swap the deterministic engine in the web app for this module
and nothing downstream (clean → index → publish) changes.

Compliance rules enforced here, not left to discipline:

  * robots.txt is fetched and parsed per host before the first request and
    re-checked on every run; disallowed paths are never requested.
  * Token-bucket rate limiting per host, honouring Crawl-delay.
  * A descriptive User-Agent with a contact URL.
  * CAPTCHAs are NEVER solved or bypassed. A challenge is recorded as a blocked
    observation and the cell is imputed downstream.
  * Only publicly displayed fares are read. No login, no personal data, the
    purchase flow is never touched.
"""

from __future__ import annotations

import asyncio
import logging
import random
import re
import time
import urllib.parse
import urllib.robotparser
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Any, Iterable

log = logging.getLogger("safar.collect")

USER_AGENT = (
    "SAFAR-Indexer/1.0 (+https://safar.stats.gov.in/bot; contact: data@safar.stats.gov.in) "
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)
ROBOTS_TOKEN = "SAFAR-Indexer"
CHALLENGE_MARKERS = (
    "captcha",
    "unusual traffic",
    "verify you are human",
    "access denied",
    "cf-challenge",
    "_Incapsula_Resource",
)


# --------------------------------------------------------------------- models


@dataclass
class RawQuote:
    """Exactly what the DOM yielded. Messy on purpose — cleaning happens later."""

    source_id: str
    carrier: str
    route_id: str
    origin: str
    destination: str
    departure: str  # YYYY-MM-DD
    lead_time: int
    fare_class: str
    flight_no: str
    fare_text: str
    tax_text: str
    fee_text: str
    seats_left: int
    refundable: bool
    baggage_kg: int
    collected_at: str


@dataclass
class SweepResult:
    source_id: str
    status: str  # ok | degraded | blocked
    started_at: str
    duration_ms: int
    requests: int
    raw_quotes: int
    http_errors: int
    retries: int
    block_events: int
    robots_allowed: bool
    notes: str
    quotes: list[RawQuote] = field(default_factory=list)


# -------------------------------------------------------------- rate limiting


class TokenBucket:
    """One bucket per host: requests/minute, crawl-delay, jitter, concurrency 1."""

    def __init__(self, per_minute: int, crawl_delay: float, jitter_pct: int = 30) -> None:
        self.per_minute = per_minute
        self.interval = 60.0 / max(per_minute, 1)
        self.crawl_delay = crawl_delay
        self.jitter_pct = jitter_pct
        self._next_slot = 0.0

    async def acquire(self) -> None:
        now = time.monotonic()
        wait = self._next_slot - now
        if wait > 0:
            await asyncio.sleep(wait)
        jitter = self.interval * self.jitter_pct / 100.0
        self._next_slot = time.monotonic() + self.interval + random.uniform(0, jitter)
        if self.crawl_delay:
            await asyncio.sleep(random.uniform(self.crawl_delay * 0.8, self.crawl_delay * 1.2))


class RobotsGate:
    """Fetch + cache robots.txt per host, honour Crawl-delay and Disallow."""

    def __init__(self, user_agent: str = ROBOTS_TOKEN) -> None:
        self.user_agent = user_agent
        self._parsers: dict[str, urllib.robotparser.RobotFileParser] = {}

    def _parser(self, url: str) -> urllib.robotparser.RobotFileParser:
        parts = urllib.parse.urlsplit(url)
        host = f"{parts.scheme}://{parts.netloc}"
        if host not in self._parsers:
            rp = urllib.robotparser.RobotFileParser()
            rp.set_url(urllib.parse.urljoin(host, "/robots.txt"))
            try:
                rp.read()
            except Exception as exc:  # noqa: BLE001 - be conservative
                log.warning("robots.txt unavailable for %s (%s); defaulting to disallow", host, exc)
                rp.parse(["User-agent: *", "Disallow: /"])
            self._parsers[host] = rp
        return self._parsers[host]

    def allowed(self, url: str) -> bool:
        return self._parser(url).can_fetch(self.user_agent, url)

    def crawl_delay(self, url: str) -> float:
        delay = self._parser(url).crawl_delay(self.user_agent)
        return float(delay) if delay else 0.0

    def refresh(self) -> None:
        """Re-check every host before a new run — policies change."""
        self._parsers.clear()


# ------------------------------------------------------------------- adapters


@dataclass
class SelectorMap:
    container: str
    fare_amount: str
    fare_class: str
    flight_number: str
    departure_time: str
    seats_left: str
    baggage: str


@dataclass
class SourceAdapter:
    source_id: str
    name: str
    kind: str  # airline | ota
    endpoint: str
    carrier: str | None
    selectors: SelectorMap
    per_minute: int
    crawl_delay: float
    render: str = "js-hydrated"

    def __post_init__(self) -> None:
        self.robots = RobotsGate()
        self.bucket = TokenBucket(self.per_minute, self.crawl_delay)

    # -- to be implemented per source -------------------------------------

    def build_url(self, origin: str, destination: str, depart: date, adults: int = 1) -> str:
        raise NotImplementedError

    def parse(self, html: str, ctx: dict[str, Any]) -> list[RawQuote]:
        raise NotImplementedError


class ScraplingFetcher:
    """Standard Playwright dynamic fetcher (no stealth, CAPTCHA bypass disabled)."""

    def __init__(self, headless: bool = True) -> None:
        self.headless = headless
        self.playwright = None
        self.browser = None
        self.context = None

    async def start(self) -> None:
        from playwright.async_api import async_playwright
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(
            headless=self.headless,
            args=["--disable-gpu", "--no-sandbox", "--disable-dev-shm-usage"]
        )
        self.context = await self.browser.new_context(
            user_agent=USER_AGENT,
            viewport={"width": 1280, "height": 720}
        )

    async def stop(self) -> None:
        if self.context:
            await self.context.close()
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()

    async def fetch(self, host: str, url: str) -> tuple[Any, int, bool]:
        """Return (parsel_selector, status, challenge_detected)."""
        page = await self.context.new_page()
        try:
            res = await page.goto(url, wait_until="networkidle", timeout=45000)
            status = res.status if res else 500
        except Exception as e:
            log.warning(f"Timeout/error fetching {url}: {e}")
            status = 500
            
        html = await page.content()
        lowered = html.lower()
        challenge = any(marker in lowered for marker in CHALLENGE_MARKERS)
        
        await page.close()
        
        import parsel
        selector = parsel.Selector(text=html)
        return selector, status, challenge


RUPEE = re.compile(r"[^0-9.]")


def parse_rupees(text: str) -> float:
    """Handles '₹12,340', 'Rs. 12340', 'INR 12,340.50'."""
    cleaned = RUPEE.sub("", text or "")
    try:
        return float(cleaned)
    except ValueError:
        return 0.0


def departure_for(day: date, lead: int) -> str:
    return (day + timedelta(days=lead)).isoformat()
