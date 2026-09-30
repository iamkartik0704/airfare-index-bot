"""Bounded exponential backoff for retryable failures (doc 10 "Failure Handling").

Only errors whose type is marked ``retryable`` are retried (network errors,
timeouts, 5xx, 429). Blocks, robots denials and parser errors are not — they
need a human or a policy decision, not another request.
"""

from __future__ import annotations

import asyncio
import random
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import TypeVar

from packages.domain.exceptions import SafarError
from packages.scraping.core.exceptions import RateLimitedError

T = TypeVar("T")


@dataclass
class RetryPolicy:
    max_attempts: int = 3
    base_delay_s: float = 2.0
    max_delay_s: float = 120.0
    jitter_ratio: float = 0.2
    rng: random.Random = field(default_factory=random.Random)

    def __post_init__(self) -> None:
        if self.max_attempts < 1:
            raise ValueError("max_attempts must be >= 1")

    def delay_for(self, attempt: int, error: BaseException | None = None) -> float:
        """Delay before attempt ``attempt + 1`` (``attempt`` is 1-based)."""
        if isinstance(error, RateLimitedError) and error.retry_after_s is not None:
            return min(error.retry_after_s, self.max_delay_s)
        delay = min(self.base_delay_s * float(2 ** (attempt - 1)), self.max_delay_s)
        return delay * (1 + self.rng.uniform(-self.jitter_ratio, self.jitter_ratio))

    @staticmethod
    def is_retryable(error: BaseException) -> bool:
        return isinstance(error, SafarError) and error.retryable

    async def run(
        self,
        operation: Callable[[], Awaitable[T]],
        *,
        sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
        on_retry: Callable[[int, BaseException, float], None] | None = None,
    ) -> T:
        attempt = 1
        while True:
            try:
                return await operation()
            except SafarError as exc:
                if not self.is_retryable(exc) or attempt >= self.max_attempts:
                    raise
                delay = self.delay_for(attempt, exc)
                if on_retry is not None:
                    on_retry(attempt, exc, delay)
                await sleep(delay)
                attempt += 1
