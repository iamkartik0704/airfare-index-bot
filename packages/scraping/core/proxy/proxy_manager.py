"""Operator-configured egress proxies (doc 04 ``ProxyManager``, doc 15).

SAFAR does not rotate IPs to evade blocks. Proxies are optional egress points
an operator may configure (e.g. an institutional gateway); a proxy is only
quarantined when *it* fails (connection errors). A source that answers with a
block or CAPTCHA is handled at the source level — back off and flag BLOCKED —
and switching proxy is never used as a response to a block.
"""

from __future__ import annotations

import itertools
import time
from collections.abc import Callable, Iterable


class ProxyManager:
    def __init__(
        self,
        proxies: Iterable[str] = (),
        quarantine_s: float = 600.0,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._proxies = list(dict.fromkeys(proxies))
        self._quarantined: dict[str, float] = {}
        self._quarantine_s = quarantine_s
        self._clock = clock
        self._cycle = itertools.cycle(self._proxies) if self._proxies else None

    @property
    def configured(self) -> bool:
        return bool(self._proxies)

    def healthy(self) -> list[str]:
        now = self._clock()
        self._quarantined = {p: t for p, t in self._quarantined.items() if t > now}
        return [p for p in self._proxies if p not in self._quarantined]

    def next_proxy(self) -> str | None:
        """Round-robin over healthy proxies; ``None`` means connect directly."""
        if self._cycle is None:
            return None
        healthy = set(self.healthy())
        if not healthy:
            return None
        for _ in range(len(self._proxies)):
            candidate = next(self._cycle)
            if candidate in healthy:
                return candidate
        return None

    def report_connection_failure(self, proxy: str) -> None:
        if proxy in self._proxies:
            self._quarantined[proxy] = self._clock() + self._quarantine_s
