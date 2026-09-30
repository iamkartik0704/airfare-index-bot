"""Playwright fetcher for JavaScript-rendered sources (doc 04 ``BrowserFetcher``).

* Blocks images, stylesheets, fonts, media and known trackers (doc 04
  "Optimization").
* Optionally captures the JSON of an XHR/fetch call the page makes
  (doc 04 "XHR/API Capture") — far more stable than parsing a React DOM.
* Reuses per-host storage state through ``SessionManager``.
* Identifies itself with the SAFAR User-Agent; no stealth or fingerprint
  masking is applied (doc 19 "Intentionally rejected").

Playwright is an optional dependency (``pip install '.[browser]'``); it is
imported lazily so the rest of the system runs without it.
"""

from __future__ import annotations

import asyncio
import time
from datetime import UTC, datetime
from typing import Any

from packages.domain.enums import FetchMode
from packages.domain.exceptions import ConfigurationError
from packages.scraping.core.exceptions import FetchTimeoutError, NetworkError
from packages.scraping.core.fetchers.base import BaseFetcher, FetchRequest, FetchResponse
from packages.scraping.core.session.session_manager import SessionManager

BLOCKED_RESOURCE_TYPES = frozenset({"image", "stylesheet", "font", "media"})
BLOCKED_TRACKER_HOSTS = (
    "google-analytics.com",
    "googletagmanager.com",
    "doubleclick.net",
    "facebook.net",
    "hotjar.com",
    "clarity.ms",
)


class BrowserFetcher(BaseFetcher):
    mode = FetchMode.BROWSER

    def __init__(
        self, session: SessionManager, *, timeout_s: float = 45.0, headless: bool = True
    ) -> None:
        self._session = session
        self._timeout_ms = int(timeout_s * 1000)
        self._headless = headless
        self._playwright: Any = None
        self._browser: Any = None
        self._lock = asyncio.Lock()

    async def _ensure_browser(self) -> Any:
        async with self._lock:
            if self._browser is None:
                try:
                    from playwright.async_api import async_playwright
                except ImportError as exc:
                    raise ConfigurationError(
                        "Playwright is not installed; install the 'browser' extra"
                    ) from exc
                self._playwright = await async_playwright().start()
                self._browser = await self._playwright.chromium.launch(headless=self._headless)
            return self._browser

    @staticmethod
    async def _route_filter(route: Any) -> None:
        req = route.request
        if req.resource_type in BLOCKED_RESOURCE_TYPES or any(
            host in req.url for host in BLOCKED_TRACKER_HOSTS
        ):
            await route.abort()
        else:
            await route.continue_()

    async def fetch(self, request: FetchRequest) -> FetchResponse:
        from playwright.async_api import Error as PlaywrightError
        from playwright.async_api import TimeoutError as PlaywrightTimeout

        browser = await self._ensure_browser()
        timeout_ms = int(request.timeout_s * 1000) if request.timeout_s else self._timeout_ms
        context = await browser.new_context(
            user_agent=self._session.user_agent,
            extra_http_headers={
                k: v
                for k, v in self._session.headers_for(request.url, request.headers).items()
                if k.lower() not in {"user-agent", "cookie"}
            },
            storage_state=self._session.storage_state(request.url),
        )
        started = time.perf_counter()
        try:
            page = await context.new_page()
            await page.route("**/*", self._route_filter)
            if request.capture_xhr:
                pattern = request.capture_xhr
                async with page.expect_response(
                    lambda r: pattern in r.url, timeout=timeout_ms
                ) as captured:
                    await page.goto(request.url, timeout=timeout_ms, wait_until="domcontentloaded")
                xhr = await captured.value
                body: bytes = await xhr.body()
                status: int = xhr.status
                headers: dict[str, str] = dict(await xhr.all_headers())
                final_url: str = xhr.url
                mode = FetchMode.XHR
            else:
                nav = await page.goto(
                    request.url, timeout=timeout_ms, wait_until="domcontentloaded"
                )
                if request.wait_for_selector:
                    await page.wait_for_selector(request.wait_for_selector, timeout=timeout_ms)
                body = (await page.content()).encode("utf-8")
                status = nav.status if nav is not None else 0
                headers = dict(await nav.all_headers()) if nav is not None else {}
                headers["content-type"] = "text/html; charset=utf-8"
                final_url = page.url
                mode = FetchMode.BROWSER
            self._session.set_storage_state(request.url, await context.storage_state())
        except PlaywrightTimeout as exc:
            raise FetchTimeoutError("browser navigation timed out", url=request.url) from exc
        except PlaywrightError as exc:
            raise NetworkError(f"browser error: {exc.message[:200]}", url=request.url) from exc
        finally:
            await context.close()

        return FetchResponse(
            request=request,
            url=final_url,
            status=status,
            body=body,
            headers={k: v for k, v in headers.items() if k.lower() != "set-cookie"},
            fetch_mode=mode,
            fetched_at=datetime.now(UTC),
            elapsed_ms=int((time.perf_counter() - started) * 1000),
        )

    async def aclose(self) -> None:
        async with self._lock:
            if self._browser is not None:
                await self._browser.close()
                self._browser = None
            if self._playwright is not None:
                await self._playwright.stop()
                self._playwright = None
