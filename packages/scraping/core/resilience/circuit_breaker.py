"""Per-source circuit breaker (doc 04: 5 consecutive failures → DEGRADED).

The breaker is a small state machine over a persisted snapshot
(``sources.consecutive_failures`` / ``sources.circuit_open_until``) so a
restarted worker keeps honouring an open circuit.

    CLOSED --N consecutive failures--> OPEN --cooldown elapsed--> HALF_OPEN
    HALF_OPEN --success--> CLOSED ;  HALF_OPEN --failure--> OPEN
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime, timedelta
from enum import StrEnum


class CircuitState(StrEnum):
    CLOSED = "CLOSED"
    OPEN = "OPEN"
    HALF_OPEN = "HALF_OPEN"


@dataclass(frozen=True)
class CircuitSnapshot:
    consecutive_failures: int = 0
    open_until: datetime | None = None


class CircuitBreaker:
    def __init__(self, failure_threshold: int = 5, cooldown_s: float = 1800.0) -> None:
        if failure_threshold < 1:
            raise ValueError("failure_threshold must be >= 1")
        self.failure_threshold = failure_threshold
        self.cooldown = timedelta(seconds=cooldown_s)

    def state(self, snap: CircuitSnapshot, now: datetime) -> CircuitState:
        if snap.open_until is None:
            return CircuitState.CLOSED
        return CircuitState.OPEN if now < snap.open_until else CircuitState.HALF_OPEN

    def allows(self, snap: CircuitSnapshot, now: datetime) -> bool:
        return self.state(snap, now) is not CircuitState.OPEN

    def record_success(self, snap: CircuitSnapshot) -> CircuitSnapshot:
        return CircuitSnapshot(consecutive_failures=0, open_until=None)

    def record_failure(self, snap: CircuitSnapshot, now: datetime) -> CircuitSnapshot:
        failures = snap.consecutive_failures + 1
        half_open = self.state(snap, now) is CircuitState.HALF_OPEN
        if half_open or failures >= self.failure_threshold:
            return replace(snap, consecutive_failures=failures, open_until=now + self.cooldown)
        return replace(snap, consecutive_failures=failures)
