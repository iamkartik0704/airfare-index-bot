"""BrowserFetcher against a local site: XHR capture, rendered DOM, resource blocking.

Runs real headless Chromium against 127.0.0.1 only. Skipped when Playwright's
browser is not installed (``playwright install chromium``).
"""

from __future__ import annotations

import json
import threading
from collections.abc import Iterator
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

from packages.domain.enums import FetchMode
from packages.scraping.core.exceptions import FetchTimeoutError
from packages.scraping.core.fetchers.base import FetchRequest
from packages.scraping.core.fetchers.browser import BrowserFetcher
from packages.scraping.core.session.session_manager import SessionManager

UA = "MoSPI-SAFAR-Bot/1.0 (+https://mospi.gov.in/safar)"

PAGE = """<!doctype html><html><head><link rel="stylesheet" href="/style.css"></head><body>
<img src="/logo.png"><div id="results"></div>
<script>
fetch('/api/availability?o=DEL').then(r => r.json()).then(d => {
  document.getElementById('results').innerHTML =
    d.flights.map(f => `<div class="card">${f}</div>`).join('');
});
</script></body></html>"""


class _Handler(BaseHTTPRequestHandler):
    hits: list[tuple[str, str]] = []

    def do_GET(self) -> None:  # noqa: N802 - http.server API
        self.hits.append((self.path, self.headers.get("User-Agent", "")))
        if self.path.startswith("/api/availability"):
            body, ctype = json.dumps({"flights": ["6E 2134", "AI 2993"]}).encode(), "application/json"
        elif self.path.startswith("/search"):
            body, ctype = PAGE.encode(), "text/html"
        else:
            body, ctype = b"", "text/plain"
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Set-Cookie", "sid=local; Path=/")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args: object) -> None:
        return


@pytest.fixture
def site() -> Iterator[str]:
    _Handler.hits = []
    server = ThreadingHTTPServer(("127.0.0.1", 0), _Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{server.server_address[1]}"
    server.shutdown()


@pytest.fixture
async def browser() -> BrowserFetcher:  # type: ignore[misc]
    pytest.importorskip("playwright")
    fetcher = BrowserFetcher(SessionManager(UA), timeout_s=20)
    try:
        await fetcher._ensure_browser()
    except Exception as exc:  # noqa: BLE001 - environment probe: no browser binary installed
        pytest.skip(f"Chromium not available: {exc}")
    yield fetcher
    await fetcher.aclose()


async def test_xhr_capture_returns_the_api_json(site: str, browser: BrowserFetcher) -> None:
    response = await browser.fetch(FetchRequest(url=f"{site}/search?o=DEL", capture_xhr="/api/availability"))
    assert response.fetch_mode is FetchMode.XHR
    assert response.json() == {"flights": ["6E 2134", "AI 2993"]}
    assert "/api/availability" in response.url


async def test_rendered_dom_blocks_assets_and_identifies_as_bot(site: str, browser: BrowserFetcher) -> None:
    response = await browser.fetch(FetchRequest(url=f"{site}/search", wait_for_selector=".card"))
    assert response.fetch_mode is FetchMode.BROWSER and response.status == 200
    cards = [c.text() for c in response.selector().css(".card")]
    assert cards == ["6E 2134", "AI 2993"]
    paths = [p for p, _ in _Handler.hits]
    assert "/logo.png" not in paths and "/style.css" not in paths  # images/CSS aborted
    assert all(ua == UA for _, ua in _Handler.hits)  # no disguised browser UA


async def test_missing_selector_times_out_as_typed_error(site: str, browser: BrowserFetcher) -> None:
    with pytest.raises(FetchTimeoutError):
        await browser.fetch(FetchRequest(url=f"{site}/search", wait_for_selector=".never", timeout_s=2))
