"""Fetcher abstraction and the unified request/response objects (docs 04, 19).

Parsers receive a ``FetchResponse`` and do not care whether it came from
``httpx``, a rendered Playwright page, an intercepted XHR, or the simulator
(doc 19 "Response objects"). ``FetchResponse`` offers JSON access and CSS
selection with ordered fallbacks (doc 19 "Adaptive selectors").
"""

from __future__ import annotations

import abc
import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime
from types import TracebackType
from typing import Any, Self

from selectolax.parser import HTMLParser, Node

from packages.domain.enums import FetchMode
from packages.scraping.core.exceptions import ParseError


@dataclass(frozen=True)
class FetchRequest:
    url: str
    method: str = "GET"
    headers: dict[str, str] = field(default_factory=dict)
    params: dict[str, str] = field(default_factory=dict)
    json_body: dict[str, Any] | None = None
    timeout_s: float | None = None
    #: Browser only: substring of the XHR/fetch URL whose JSON response to capture.
    capture_xhr: str | None = None
    #: Browser only: CSS selector that signals the results have rendered.
    wait_for_selector: str | None = None
    #: Free-form context for the adapter (e.g. which leg this request is for).
    meta: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class FetchResponse:
    request: FetchRequest
    url: str
    status: int
    body: bytes
    headers: dict[str, str]
    fetch_mode: FetchMode
    fetched_at: datetime
    elapsed_ms: int

    @property
    def content_type(self) -> str | None:
        for key, value in self.headers.items():
            if key.lower() == "content-type":
                return value
        return None

    @property
    def sha256(self) -> str:
        return hashlib.sha256(self.body).hexdigest()

    @property
    def text(self) -> str:
        return self.body.decode("utf-8", errors="replace")

    def json(self) -> Any:
        try:
            return json.loads(self.body)
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            raise ParseError("response body is not valid JSON", url=self.url) from exc

    def selector(self) -> Selector:
        return Selector(HTMLParser(self.body))


class Selector:
    """Thin wrapper over selectolax nodes with fallback selector lists."""

    def __init__(self, node: HTMLParser | Node) -> None:
        self._node = node

    def css(self, *selectors: str) -> list[Selector]:
        """Nodes for the first selector in ``selectors`` that matches anything."""
        for sel in selectors:
            found = self._node.css(sel)
            if found:
                return [Selector(n) for n in found]
        return []

    def css_first(self, *selectors: str) -> Selector | None:
        matches = self.css(*selectors)
        return matches[0] if matches else None

    def text(self, *selectors: str, default: str | None = None) -> str | None:
        """Stripped text of the first match, or ``default``."""
        target: Selector | None = self if not selectors else self.css_first(*selectors)
        if target is None:
            return default
        raw = target._node.text(separator=" ", strip=True)
        return " ".join(raw.split()) or default

    def attr(self, name: str, *selectors: str) -> str | None:
        target = self if not selectors else self.css_first(*selectors)
        if target is None:
            return None
        node = target._node
        attributes = node.attributes if isinstance(node, Node) else {}
        return attributes.get(name)

    def require_text(self, *selectors: str, field_name: str) -> str:
        value = self.text(*selectors)
        if value is None:
            raise ParseError(
                "mandatory field missing", field=field_name, selectors="|".join(selectors)
            )
        return value


class BaseFetcher(abc.ABC):
    """``fetch(request) -> response`` regardless of transport (doc 04)."""

    mode: FetchMode

    @abc.abstractmethod
    async def fetch(self, request: FetchRequest) -> FetchResponse: ...

    async def aclose(self) -> None:  # noqa: B027 - optional hook for stateless fetchers
        """Release transport resources."""

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        await self.aclose()
