from __future__ import annotations

import random
from datetime import UTC, datetime, timedelta

import pytest

from packages.domain.exceptions import ConfigurationError
from packages.scraping.core.exceptions import NetworkError, ParseError, RateLimitedError
from packages.scraping.core.proxy.proxy_manager import ProxyManager
from packages.scraping.core.rate_limit.limiter import DomainRateLimiter
from packages.scraping.core.resilience.circuit_breaker import (
    CircuitBreaker,
    CircuitSnapshot,
    CircuitState,
)
from packages.scraping.core.resilience.retry import RetryPolicy
from packages.scraping.core.session.session_manager import SessionManager


class FakeClock:
    def __init__(self) -> None:
        self.now = 1000.0
        self.slept: list[float] = []

    def __call__(self) -> float:
        return self.now

    async def sleep(self, seconds: float) -> None:
        self.slept.append(seconds)
        self.now += seconds


class TestRateLimiter:
    async def test_spacing_is_max_of_rpm_and_crawl_delay(self) -> None:
        clock = FakeClock()
        limiter = DomainRateLimiter(clock=clock, sleep=clock.sleep)
        limiter.configure("h", requests_per_minute=6, crawl_delay_s=15)
        assert limiter.interval_for("h") == 15
        await limiter.acquire("h")
        await limiter.acquire("h")
        await limiter.acquire("h")
        assert clock.slept == [15, 15]

    async def test_hosts_are_independent(self) -> None:
        clock = FakeClock()
        limiter = DomainRateLimiter(clock=clock, sleep=clock.sleep)
        limiter.configure("a", requests_per_minute=1)
        limiter.configure("b", requests_per_minute=1)
        await limiter.acquire("a")
        await limiter.acquire("b")
        assert clock.slept == []

    async def test_pause_pushes_next_slot(self) -> None:
        clock = FakeClock()
        limiter = DomainRateLimiter(clock=clock, sleep=clock.sleep)
        limiter.configure("h", requests_per_minute=60)
        await limiter.acquire("h")
        limiter.pause("h", 30)
        await limiter.acquire("h")
        assert clock.slept == [30]

    def test_unconfigured_host_is_an_error(self) -> None:
        with pytest.raises(KeyError):
            DomainRateLimiter()._state("x")


class TestRetryPolicy:
    async def test_retries_retryable_errors_then_succeeds(self) -> None:
        attempts = []

        async def op() -> str:
            attempts.append(1)
            if len(attempts) < 3:
                raise NetworkError("reset")
            return "ok"

        slept: list[float] = []

        async def sleep(s: float) -> None:
            slept.append(s)

        policy = RetryPolicy(max_attempts=3, base_delay_s=2, jitter_ratio=0, rng=random.Random(1))
        assert await policy.run(op, sleep=sleep) == "ok"
        assert slept == [2, 4]  # exponential

    async def test_non_retryable_error_is_raised_immediately(self) -> None:
        calls = 0

        async def op() -> None:
            nonlocal calls
            calls += 1
            raise ParseError("bad")

        with pytest.raises(ParseError):
            await RetryPolicy(max_attempts=5).run(op, sleep=_no_sleep)
        assert calls == 1

    async def test_gives_up_after_max_attempts(self) -> None:
        async def op() -> None:
            raise NetworkError("down")

        with pytest.raises(NetworkError):
            await RetryPolicy(max_attempts=2, base_delay_s=0).run(op, sleep=_no_sleep)

    def test_retry_after_is_honoured_and_capped(self) -> None:
        policy = RetryPolicy(max_delay_s=60)
        assert policy.delay_for(1, RateLimitedError("x", retry_after_s=30)) == 30
        assert policy.delay_for(1, RateLimitedError("x", retry_after_s=600)) == 60


async def _no_sleep(_: float) -> None:
    return None


class TestCircuitBreaker:
    def test_opens_after_threshold_and_half_opens_after_cooldown(self) -> None:
        breaker = CircuitBreaker(failure_threshold=3, cooldown_s=60)
        now = datetime(2026, 9, 30, tzinfo=UTC)
        snap = CircuitSnapshot()
        for _ in range(2):
            snap = breaker.record_failure(snap, now)
        assert breaker.state(snap, now) is CircuitState.CLOSED
        snap = breaker.record_failure(snap, now)
        assert breaker.state(snap, now) is CircuitState.OPEN
        assert not breaker.allows(snap, now)
        later = now + timedelta(seconds=61)
        assert breaker.state(snap, later) is CircuitState.HALF_OPEN
        assert breaker.allows(snap, later)
        reopened = breaker.record_failure(snap, later)  # trial failed
        assert breaker.state(reopened, later) is CircuitState.OPEN
        assert breaker.state(breaker.record_success(reopened), later) is CircuitState.CLOSED


class TestSessionAndProxy:
    def test_session_identifies_as_bot_and_keeps_cookies_per_host(self) -> None:
        session = SessionManager("MoSPI-SAFAR-Bot/1.0 (+https://mospi.gov.in/safar)")
        session.absorb_set_cookie("https://a.test/x", ["sid=1; Path=/", "lang=en"])
        headers = session.headers_for("https://a.test/y", {"User-Agent": "Mozilla/5.0 Chrome"})
        assert headers["User-Agent"].startswith("MoSPI-SAFAR-Bot")
        assert headers["Cookie"] == "lang=en; sid=1"
        assert "Cookie" not in session.headers_for("https://b.test/")

    def test_disguised_user_agent_is_rejected(self) -> None:
        with pytest.raises(ConfigurationError):
            SessionManager("Mozilla/5.0 (Windows NT 10.0) Chrome/120")

    def test_session_state_round_trips_to_disk(self, tmp_path) -> None:  # type: ignore[no-untyped-def]
        session = SessionManager("SAFAR-bot")
        session.absorb_set_cookie("https://a.test/", ["sid=9"])
        session.save(tmp_path / "s.json")
        restored = SessionManager("SAFAR-bot")
        restored.load(tmp_path / "s.json")
        assert restored.cookies("https://a.test/") == {"sid": "9"}

    def test_proxies_rotate_and_quarantine_only_on_connection_failure(self) -> None:
        clock = FakeClock()
        proxies = ProxyManager(["http://p1", "http://p2"], quarantine_s=10, clock=clock)
        assert {proxies.next_proxy(), proxies.next_proxy()} == {"http://p1", "http://p2"}
        proxies.report_connection_failure("http://p1")
        assert proxies.healthy() == ["http://p2"]
        clock.now += 11
        assert proxies.healthy() == ["http://p1", "http://p2"]
        assert ProxyManager().next_proxy() is None
