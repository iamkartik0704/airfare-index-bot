"""robots.txt compliance (doc 15 "Robots.txt Awareness").

``RobotsPolicy`` implements RFC 9309 matching, which the standard library's
``urllib.robotparser`` does not: ``*``/``$`` wildcards, longest-match wins,
``Allow`` wins ties. It also tolerates absolute-URL rules
(``Disallow: https://www.spicejet.com/api/v1``) that some Indian airline sites
publish, and reads the non-standard ``Crawl-delay``.

``RobotsGate`` fetches and caches one policy per host. Availability rules:

* 2xx → parse.
* 404 / 410 → no robots.txt: everything allowed (RFC 9309 §2.3.1.3).
* other 4xx (401/403/…) → treated as *disallow all* — the host is refusing us.
* 5xx / network failure → unreachable → disallow all when ``fail_closed``
  (RFC 9309 §2.3.1.4), which is the default.
"""

from __future__ import annotations

import asyncio
import re
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from urllib.parse import unquote, urlsplit

import httpx

RobotsFetch = Callable[[str], Awaitable[tuple[int, str]]]


@dataclass(frozen=True)
class _Rule:
    allow: bool
    pattern: str
    regex: re.Pattern[str]

    @property
    def specificity(self) -> int:
        return len(self.pattern)


@dataclass
class _Group:
    agents: list[str] = field(default_factory=list)
    rules: list[_Rule] = field(default_factory=list)
    crawl_delay: float | None = None


def _compile(pattern: str) -> re.Pattern[str]:
    anchored = pattern.endswith("$")
    body = pattern[:-1] if anchored else pattern
    regex = "".join(".*" if ch == "*" else re.escape(ch) for ch in body)
    return re.compile(regex + ("$" if anchored else ""))


def _normalize_rule_path(value: str, host: str | None) -> str | None:
    value = value.strip()
    if value.startswith(("http://", "https://")):
        parts = urlsplit(value)
        if host is not None and parts.netloc.lower() != host.lower():
            return None  # a rule for another host does not apply here
        value = parts.path or "/"
        if parts.query:
            value += "?" + parts.query
    if value and not value.startswith(("/", "*")):
        value = "/" + value
    return unquote(value)


class RobotsPolicy:
    """Parsed robots.txt for one host."""

    def __init__(self, groups: list[_Group], *, allow_all: bool = False, deny_all: bool = False):
        self._groups = groups
        self.allow_all = allow_all
        self.deny_all = deny_all

    @classmethod
    def parse(cls, content: str, host: str | None = None) -> RobotsPolicy:
        groups: list[_Group] = []
        current: _Group | None = None
        last_was_agent = False
        for raw_line in content.splitlines():
            line = raw_line.split("#", 1)[0].strip()
            if not line or ":" not in line:
                continue
            key, value = (part.strip() for part in line.split(":", 1))
            key = key.lower()
            if key == "user-agent":
                if current is None or not last_was_agent:
                    current = _Group()
                    groups.append(current)
                current.agents.append(value.lower())
                last_was_agent = True
                continue
            last_was_agent = False
            if current is None:
                continue
            if key in ("allow", "disallow"):
                path = _normalize_rule_path(value, host)
                if path is None or (key == "disallow" and path == ""):
                    continue  # empty Disallow = allow everything
                if path == "":
                    continue
                current.rules.append(_Rule(key == "allow", path, _compile(path)))
            elif key == "crawl-delay":
                try:
                    current.crawl_delay = float(value)
                except ValueError:
                    continue
        return cls(groups)

    @classmethod
    def allowing_all(cls) -> RobotsPolicy:
        return cls([], allow_all=True)

    @classmethod
    def denying_all(cls) -> RobotsPolicy:
        return cls([], deny_all=True)

    def _groups_for(self, agent_token: str) -> list[_Group]:
        token = agent_token.lower()
        specific = [
            g
            for g in self._groups
            if any(a != "*" and (a == token or a in token) for a in g.agents)
        ]
        if specific:
            return specific
        return [g for g in self._groups if "*" in g.agents]

    def can_fetch(self, agent_token: str, url: str) -> bool:
        if self.deny_all:
            return False
        if self.allow_all:
            return True
        parts = urlsplit(url)
        path = unquote(parts.path or "/") + (f"?{parts.query}" if parts.query else "")
        if path == "/robots.txt":
            return True
        best: _Rule | None = None
        for group in self._groups_for(agent_token):
            for rule in group.rules:
                if rule.regex.match(path) and (
                    best is None
                    or rule.specificity > best.specificity
                    or (rule.specificity == best.specificity and rule.allow and not best.allow)
                ):
                    best = rule
        return True if best is None else best.allow

    def crawl_delay(self, agent_token: str) -> float | None:
        delays = [g.crawl_delay for g in self._groups_for(agent_token) if g.crawl_delay is not None]
        return max(delays) if delays else None


@dataclass(frozen=True)
class RobotsDecision:
    allowed: bool
    crawl_delay_s: float | None
    reason: str


async def _default_fetch(url: str, user_agent: str, timeout_s: float) -> tuple[int, str]:
    async with httpx.AsyncClient(timeout=timeout_s, follow_redirects=True) as client:
        resp = await client.get(url, headers={"User-Agent": user_agent})
        return resp.status_code, resp.text


class RobotsGate:
    """Per-host robots.txt cache with TTL; call ``check(url)`` before every request."""

    def __init__(
        self,
        *,
        agent_token: str,
        user_agent: str,
        fail_closed: bool = True,
        ttl_s: float = 6 * 3600,
        timeout_s: float = 15.0,
        fetch: RobotsFetch | None = None,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._agent = agent_token
        self._fail_closed = fail_closed
        self._ttl = ttl_s
        self._clock = clock
        self._fetch: RobotsFetch = fetch or (lambda u: _default_fetch(u, user_agent, timeout_s))
        self._cache: dict[str, tuple[float, RobotsPolicy, str]] = {}
        self._locks: dict[str, asyncio.Lock] = {}

    async def _policy(self, scheme: str, host: str) -> tuple[RobotsPolicy, str]:
        key = f"{scheme}://{host}"
        cached = self._cache.get(key)
        if cached and cached[0] > self._clock():
            return cached[1], cached[2]
        lock = self._locks.setdefault(key, asyncio.Lock())
        async with lock:
            cached = self._cache.get(key)
            if cached and cached[0] > self._clock():
                return cached[1], cached[2]
            policy, note = await self._load(key, host)
            self._cache[key] = (self._clock() + self._ttl, policy, note)
            return policy, note

    async def _load(self, origin: str, host: str) -> tuple[RobotsPolicy, str]:
        try:
            status, body = await self._fetch(f"{origin}/robots.txt")
        except (httpx.HTTPError, OSError) as exc:
            note = f"robots.txt unreachable ({exc.__class__.__name__})"
            return (
                RobotsPolicy.denying_all() if self._fail_closed else RobotsPolicy.allowing_all()
            ), note
        if 200 <= status < 300:
            return RobotsPolicy.parse(body, host=host), "robots.txt parsed"
        if status in (404, 410):
            return RobotsPolicy.allowing_all(), f"no robots.txt (HTTP {status})"
        if 400 <= status < 500:
            return RobotsPolicy.denying_all(), f"robots.txt refused (HTTP {status})"
        note = f"robots.txt unavailable (HTTP {status})"
        return (
            RobotsPolicy.denying_all() if self._fail_closed else RobotsPolicy.allowing_all()
        ), note

    async def check(self, url: str) -> RobotsDecision:
        parts = urlsplit(url)
        if parts.scheme not in ("http", "https"):
            return RobotsDecision(True, None, "non-HTTP source")
        policy, note = await self._policy(parts.scheme, parts.netloc.lower())
        allowed = policy.can_fetch(self._agent, url)
        reason = note if allowed else f"disallowed by robots.txt: {note}"
        return RobotsDecision(allowed, policy.crawl_delay(self._agent), reason)

    def invalidate(self, host: str | None = None) -> None:
        """Re-read robots.txt before the next request (doc 15: policies change)."""
        if host is None:
            self._cache.clear()
        else:
            self._cache = {k: v for k, v in self._cache.items() if not k.endswith(f"//{host}")}
