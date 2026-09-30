"""Per-domain rate limiting (doc 15 "Rate Limiting", doc 10 "Concurrency Control").

Each host gets a token bucket of capacity 1 — i.e. strict spacing, no bursts.
The spacing is the larger of ``60 / requests_per_minute`` and the robots.txt /
policy ``Crawl-delay``. A ``pause`` (e.g. after HTTP 429 ``Retry-After``) pushes
the host's next slot into the future for every caller.

Limits are enforced per worker process; cross-process concurrency is bounded
by the job queue's per-source running-job cap.
"""

from __future__ import annotations

import asyncio
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass

Clock = Callable[[], float]
Sleep = Callable[[float], Awaitable[None]]


@dataclass
class _HostState:
    interval_s: float
    next_slot: float
    lock: asyncio.Lock


class DomainRateLimiter:
    def __init__(self, clock: Clock = time.monotonic, sleep: Sleep = asyncio.sleep) -> None:
        self._clock = clock
        self._sleep = sleep
        self._hosts: dict[str, _HostState] = {}

    def configure(self, host: str, *, requests_per_minute: int, crawl_delay_s: float = 0.0) -> None:
        if requests_per_minute <= 0:
            raise ValueError("requests_per_minute must be positive")
        interval = max(60.0 / requests_per_minute, crawl_delay_s)
        state = self._hosts.get(host)
        if state is None:
            self._hosts[host] = _HostState(interval, self._clock(), asyncio.Lock())
        else:
            state.interval_s = interval

    def interval_for(self, host: str) -> float:
        return self._state(host).interval_s

    def _state(self, host: str) -> _HostState:
        try:
            return self._hosts[host]
        except KeyError as exc:
            raise KeyError(f"rate limit not configured for host {host!r}") from exc

    async def acquire(self, host: str) -> float:
        """Wait for the host's next slot. Returns the seconds waited."""
        state = self._state(host)
        async with state.lock:
            now = self._clock()
            wait = max(0.0, state.next_slot - now)
            if wait:
                await self._sleep(wait)
            state.next_slot = max(state.next_slot, now) + state.interval_s
            return wait

    def pause(self, host: str, seconds: float) -> None:
        state = self._state(host)
        state.next_slot = max(state.next_slot, self._clock() + seconds)


class ConcurrencyLimiter:
    """At most ``limit`` in-flight requests per source (doc 10: 1–3 per source)."""

    def __init__(self) -> None:
        self._semaphores: dict[str, asyncio.Semaphore] = {}

    def slot(self, key: str, limit: int) -> asyncio.Semaphore:
        semaphore = self._semaphores.get(key)
        if semaphore is None:
            semaphore = asyncio.Semaphore(max(1, limit))
            self._semaphores[key] = semaphore
        return semaphore
