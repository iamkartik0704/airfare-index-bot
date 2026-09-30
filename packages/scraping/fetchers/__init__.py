"""Public fetcher façade and factory (docs 04, 19; see decisions D5).

Adapters never construct transports. The factory returns the shared fetcher
for a source's ``fetch_mode`` so switching a source between ``httpx`` and
Playwright is a one-line change in ``sources.yaml`` (doc 19 "Fetcher
abstraction").
"""

from __future__ import annotations

from packages.config.settings import ScrapingSettings
from packages.domain.exceptions import ConfigurationError
from packages.scraping.core.fetchers.base import BaseFetcher, FetchRequest, FetchResponse
from packages.scraping.core.fetchers.browser import BrowserFetcher
from packages.scraping.core.fetchers.http import HttpFetcher
from packages.scraping.core.proxy.proxy_manager import ProxyManager
from packages.scraping.core.session.session_manager import SessionManager


class FetcherFactory:
    """Owns one fetcher per mode for the lifetime of a worker process."""

    def __init__(self, settings: ScrapingSettings) -> None:
        self._settings = settings
        self.session = SessionManager(settings.user_agent)
        self._proxies = ProxyManager(p.get_secret_value() for p in settings.proxies)
        self._fetchers: dict[str, BaseFetcher] = {}

    def register(self, mode: str, fetcher: BaseFetcher) -> None:
        """Install a fetcher for a mode (used by tests and by the simulator)."""
        self._fetchers[mode] = fetcher

    def get(self, mode: str) -> BaseFetcher:
        fetcher = self._fetchers.get(mode)
        if fetcher is not None:
            return fetcher
        if mode == "http":
            fetcher = HttpFetcher(
                self.session, timeout_s=self._settings.request_timeout_s, proxies=self._proxies
            )
        elif mode == "browser":
            fetcher = BrowserFetcher(
                self.session,
                timeout_s=self._settings.request_timeout_s + 15,
                headless=self._settings.browser_headless,
            )
        elif mode == "simulated":
            from packages.scraping.sources.simulated.fetcher import SimulatedFetcher

            fetcher = SimulatedFetcher()
        else:
            raise ConfigurationError("unknown fetch mode", mode=mode)
        self._fetchers[mode] = fetcher
        return fetcher

    async def aclose(self) -> None:
        for fetcher in self._fetchers.values():
            await fetcher.aclose()
        self._fetchers.clear()


__all__ = [
    "BaseFetcher",
    "BrowserFetcher",
    "FetchRequest",
    "FetchResponse",
    "FetcherFactory",
    "HttpFetcher",
]
