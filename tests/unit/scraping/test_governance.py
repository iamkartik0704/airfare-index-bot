from __future__ import annotations

import httpx
import pytest

from packages.scraping.core.exceptions import (
    HttpStatusError,
    RateLimitedError,
    SourceBlockedError,
)
from packages.scraping.core.governance.blocking import detect_block, raise_for_response
from packages.scraping.core.governance.robots import RobotsGate, RobotsPolicy
from tests.helpers import make_response

AGENT = "MoSPI-SAFAR-Bot"

# Rules as published by real Indian sources (robots.txt snapshot 2026-09-30).
SPICEJET = """
User-agent: googlebot
Disallow:
User-agent: *
Disallow:
Disallow: /cgi-bin/
Disallow: https://www.spicejet.com/api/v1
Disallow: https://www.spicejet.com/public/
"""
IXIGO = """
User-agent: *
Disallow: /search/result/
Disallow: /flights/search
Disallow: /api/
crawl-delay: 10
"""


class TestRobotsPolicy:
    def test_absolute_url_rules_apply_to_their_host(self) -> None:
        policy = RobotsPolicy.parse(SPICEJET, host="www.spicejet.com")
        assert not policy.can_fetch(AGENT, "https://www.spicejet.com/api/v1/search?x=1")
        assert not policy.can_fetch(AGENT, "https://www.spicejet.com/public/file")
        assert policy.can_fetch(AGENT, "https://www.spicejet.com/search?from=DEL")

    def test_crawl_delay_and_disallow(self) -> None:
        policy = RobotsPolicy.parse(IXIGO, host="www.ixigo.com")
        assert not policy.can_fetch(AGENT, "https://www.ixigo.com/flights/search?from=DEL")
        assert policy.can_fetch(AGENT, "https://www.ixigo.com/flights")
        assert policy.crawl_delay(AGENT) == 10

    def test_longest_match_wins_and_allow_wins_ties(self) -> None:
        policy = RobotsPolicy.parse(
            "User-agent: *\nDisallow: /flights\nAllow: /flights/public\nAllow: /x\nDisallow: /x\n"
        )
        assert not policy.can_fetch(AGENT, "https://h/flights/search")
        assert policy.can_fetch(AGENT, "https://h/flights/public/1")
        assert policy.can_fetch(AGENT, "https://h/x")

    def test_wildcards_and_anchor(self) -> None:
        policy = RobotsPolicy.parse("User-agent: *\nDisallow: /*.json$\nDisallow: /listing*\n")
        assert not policy.can_fetch(AGENT, "https://h/a/b.json")
        assert policy.can_fetch(AGENT, "https://h/a/b.json?x=1")
        assert not policy.can_fetch(AGENT, "https://h/listing-page")

    def test_specific_group_overrides_star(self) -> None:
        policy = RobotsPolicy.parse(
            "User-agent: *\nDisallow: /\n\nUser-agent: MoSPI-SAFAR-Bot\nDisallow: /private\n"
        )
        assert policy.can_fetch(AGENT, "https://h/search")
        assert not policy.can_fetch("OtherBot", "https://h/search")

    def test_robots_txt_itself_is_always_allowed(self) -> None:
        assert RobotsPolicy.parse("User-agent: *\nDisallow: /").can_fetch(AGENT, "https://h/robots.txt")


class TestRobotsGate:
    async def _gate(self, status: int, body: str = "", *, fail_closed: bool = True) -> RobotsGate:
        async def fetch(url: str) -> tuple[int, str]:
            return status, body

        return RobotsGate(agent_token=AGENT, user_agent=AGENT, fetch=fetch, fail_closed=fail_closed)

    async def test_missing_robots_allows(self) -> None:
        gate = await self._gate(404)
        assert (await gate.check("https://h/search")).allowed

    async def test_forbidden_robots_denies(self) -> None:
        gate = await self._gate(403)
        decision = await gate.check("https://h/search")
        assert not decision.allowed
        assert "403" in decision.reason

    async def test_unreachable_robots_fails_closed_by_default(self) -> None:
        async def boom(url: str) -> tuple[int, str]:
            raise httpx.ConnectError("refused")

        gate = RobotsGate(agent_token=AGENT, user_agent=AGENT, fetch=boom)
        assert not (await gate.check("https://h/search")).allowed
        open_gate = RobotsGate(agent_token=AGENT, user_agent=AGENT, fetch=boom, fail_closed=False)
        assert (await open_gate.check("https://h/search")).allowed

    async def test_server_error_fails_closed(self) -> None:
        gate = await self._gate(503)
        assert not (await gate.check("https://h/a")).allowed

    async def test_policy_cached_until_invalidated(self) -> None:
        calls = []

        async def fetch(url: str) -> tuple[int, str]:
            calls.append(url)
            return 200, "User-agent: *\nDisallow: /no"

        gate = RobotsGate(agent_token=AGENT, user_agent=AGENT, fetch=fetch)
        await gate.check("https://h/a")
        await gate.check("https://h/b")
        assert calls == ["https://h/robots.txt"]
        gate.invalidate("h")
        await gate.check("https://h/c")
        assert len(calls) == 2

    async def test_simulator_urls_bypass_robots(self) -> None:
        gate = await self._gate(403)
        assert (await gate.check("sim://market/search")).allowed


class TestBlockDetection:
    def test_status_403_is_a_block(self) -> None:
        assert detect_block(make_response("nope", status=403)).blocked

    @pytest.mark.parametrize(
        "html",
        [
            "<html><title>Just a moment...</title><div class='cf-browser-verification'></div></html>",
            "<html><body>Please verify you are human</body></html>",
            "<html><script src='https://geo.captcha-delivery.com/c.js'></script></html>",
        ],
    )
    def test_challenge_pages_are_blocks(self, html: str) -> None:
        verdict = detect_block(make_response(html))
        assert verdict.blocked and verdict.reason

    def test_login_recaptcha_on_normal_page_is_not_a_block(self) -> None:
        html = "<html><body><div class='g-recaptcha'></div><div class='flight'>6E 201</div></body></html>"
        assert not detect_block(make_response(html)).blocked

    def test_json_mentioning_captcha_is_not_a_block(self) -> None:
        assert not detect_block(make_response({"captchaRequired": False, "flights": []})).blocked

    def test_raise_for_response_classifies(self) -> None:
        with pytest.raises(RateLimitedError) as rl:
            raise_for_response(make_response("", status=429, headers={"Retry-After": "12"}), source_id="s")
        assert rl.value.retry_after_s == 12 and rl.value.retryable
        with pytest.raises(SourceBlockedError):
            raise_for_response(make_response("x", status=403), source_id="s")
        with pytest.raises(HttpStatusError) as server:
            raise_for_response(make_response("x", status=502), source_id="s")
        assert server.value.retryable
        with pytest.raises(HttpStatusError) as client:
            raise_for_response(make_response("x", status=404), source_id="s")
        assert not client.value.retryable
        raise_for_response(make_response({"ok": True}), source_id="s")  # no error
