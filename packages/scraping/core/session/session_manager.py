"""Per-source session state (doc 04 ``SessionManager``).

Keeps cookies and browser storage state per host across the requests of a
sweep, so a source sees one continuous, transparently identified client
instead of a stream of fresh sessions. Headers always carry the descriptive
SAFAR User-Agent (doc 15 "Transparent Identification"); no browser
fingerprints are spoofed.

State can be persisted to disk between worker restarts (``save``/``load``).
"""

from __future__ import annotations

import json
from http.cookies import SimpleCookie
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from packages.domain.exceptions import ConfigurationError


class SessionManager:
    def __init__(self, user_agent: str, extra_headers: dict[str, str] | None = None) -> None:
        if "bot" not in user_agent.lower():
            # Guard against someone configuring a disguised browser UA (doc 15/19).
            raise ConfigurationError("User-Agent must identify SAFAR as a bot", ua=user_agent)
        self.user_agent = user_agent
        self._base_headers = {
            "User-Agent": user_agent,
            "Accept-Language": "en-IN,en;q=0.8",
            **(extra_headers or {}),
        }
        self._cookies: dict[str, dict[str, str]] = {}
        self._storage_state: dict[str, dict[str, Any]] = {}

    @staticmethod
    def host(url: str) -> str:
        return urlsplit(url).netloc.lower()

    def headers_for(
        self, url: str, request_headers: dict[str, str] | None = None
    ) -> dict[str, str]:
        headers = {**self._base_headers, **(request_headers or {})}
        headers["User-Agent"] = self.user_agent  # adapters may not override identification
        jar = self._cookies.get(self.host(url))
        if jar:
            headers["Cookie"] = "; ".join(f"{k}={v}" for k, v in sorted(jar.items()))
        return headers

    def absorb_set_cookie(self, url: str, set_cookie_values: list[str]) -> None:
        jar = self._cookies.setdefault(self.host(url), {})
        for raw in set_cookie_values:
            parsed: SimpleCookie = SimpleCookie()
            parsed.load(raw)
            for name, morsel in parsed.items():
                jar[name] = morsel.value

    def cookies(self, url: str) -> dict[str, str]:
        return dict(self._cookies.get(self.host(url), {}))

    def storage_state(self, url: str) -> dict[str, Any] | None:
        return self._storage_state.get(self.host(url))

    def set_storage_state(self, url: str, state: dict[str, Any]) -> None:
        self._storage_state[self.host(url)] = state

    def clear(self, url: str | None = None) -> None:
        if url is None:
            self._cookies.clear()
            self._storage_state.clear()
            return
        host = self.host(url)
        self._cookies.pop(host, None)
        self._storage_state.pop(host, None)

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {"cookies": self._cookies, "storage_state": self._storage_state}
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps(payload), encoding="utf-8")
        tmp.replace(path)

    def load(self, path: Path) -> None:
        if not path.exists():
            return
        payload = json.loads(path.read_text(encoding="utf-8"))
        self._cookies = {h: dict(c) for h, c in payload.get("cookies", {}).items()}
        self._storage_state = dict(payload.get("storage_state", {}))
