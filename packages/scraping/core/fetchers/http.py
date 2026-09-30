"""HTTP fetcher on ``httpx`` (doc 04 ``HttpFetcher``).

Used for JSON endpoints and server-rendered pages. Connection pooling comes
from a long-lived ``AsyncClient`` per egress (direct or configured proxy).
Transport failures are mapped to the typed scraping errors; HTTP statuses are
returned, not raised — classifying 429/403/5xx is the engine's job.
"""

from __future__ import annotations

import time
from datetime import UTC, datetime

import httpx

from packages.domain.enums import FetchMode
from packages.scraping.core.exceptions import FetchTimeoutError, NetworkError
from packages.scraping.core.fetchers.base import BaseFetcher, FetchRequest, FetchResponse
from packages.scraping.core.proxy.proxy_manager import ProxyManager
from packages.scraping.core.session.session_manager import SessionManager


class HttpFetcher(BaseFetcher):
    mode = FetchMode.HTTP

    def __init__(
        self,
        session: SessionManager,
        *,
        timeout_s: float = 30.0,
        proxies: ProxyManager | None = None,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._session = session
        self._timeout_s = timeout_s
        self._proxies = proxies or ProxyManager()
        self._transport = transport
        self._clients: dict[str | None, httpx.AsyncClient] = {}

    def _client(self, proxy: str | None) -> httpx.AsyncClient:
        client = self._clients.get(proxy)
        if client is None:
            client = httpx.AsyncClient(
                proxy=proxy,
                transport=self._transport,
                follow_redirects=True,
                timeout=self._timeout_s,
            )
            self._clients[proxy] = client
        return client

    async def fetch(self, request: FetchRequest) -> FetchResponse:
        proxy = self._proxies.next_proxy()
        client = self._client(proxy)
        headers = self._session.headers_for(request.url, request.headers)
        started = time.perf_counter()
        try:
            resp = await client.request(
                request.method,
                request.url,
                params=request.params or None,
                json=request.json_body,
                headers=headers,
                timeout=request.timeout_s or self._timeout_s,
            )
        except httpx.TimeoutException as exc:
            raise FetchTimeoutError("request timed out", url=request.url) from exc
        except httpx.TransportError as exc:
            if proxy is not None:
                self._proxies.report_connection_failure(proxy)
            raise NetworkError(
                f"transport error: {exc.__class__.__name__}", url=request.url
            ) from exc

        self._session.absorb_set_cookie(str(resp.url), resp.headers.get_list("set-cookie"))
        return FetchResponse(
            request=request,
            url=str(resp.url),
            status=resp.status_code,
            body=resp.content,
            headers={k: v for k, v in resp.headers.items() if k.lower() != "set-cookie"},
            fetch_mode=self.mode,
            fetched_at=datetime.now(UTC),
            elapsed_ms=int((time.perf_counter() - started) * 1000),
        )

    async def aclose(self) -> None:
        for client in self._clients.values():
            await client.aclose()
        self._clients.clear()
