"""Test helpers: fixtures on disk, fake transports, response builders."""

from __future__ import annotations

import json
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from alembic.config import Config

from packages.config.settings import REPO_ROOT
from packages.domain.enums import FetchMode
from packages.scraping.core.fetchers.base import BaseFetcher, FetchRequest, FetchResponse
from packages.scraping.core.governance.robots import RobotsGate

FIXTURES = Path(__file__).parent / "fixtures"


def alembic_config(url: str) -> Config:
    cfg = Config(str(REPO_ROOT / "alembic.ini"))
    cfg.set_main_option("sqlalchemy.url", url)
    return cfg


def load_fixture(*parts: str) -> bytes:
    return FIXTURES.joinpath(*parts).read_bytes()


def make_response(
    body: bytes | str | dict[str, Any] | list[Any],
    *,
    status: int = 200,
    url: str = "https://example.test/search",
    content_type: str | None = None,
    headers: dict[str, str] | None = None,
    mode: FetchMode = FetchMode.HTTP,
) -> FetchResponse:
    if isinstance(body, dict | list):
        raw = json.dumps(body).encode()
        content_type = content_type or "application/json"
    elif isinstance(body, str):
        raw = body.encode()
        content_type = content_type or "text/html; charset=utf-8"
    else:
        raw = body
    hdrs = {"content-type": content_type or "application/octet-stream", **(headers or {})}
    return FetchResponse(
        request=FetchRequest(url=url),
        url=url,
        status=status,
        body=raw,
        headers=hdrs,
        fetch_mode=mode,
        fetched_at=datetime.now(UTC),
        elapsed_ms=5,
    )


class ScriptedFetcher(BaseFetcher):
    """Returns queued responses (or raises queued exceptions) in order."""

    mode = FetchMode.HTTP

    def __init__(
        self, script: list[FetchResponse | Exception | Callable[[FetchRequest], FetchResponse]]
    ):
        self.script = list(script)
        self.requests: list[FetchRequest] = []

    async def fetch(self, request: FetchRequest) -> FetchResponse:
        self.requests.append(request)
        if not self.script:
            raise AssertionError(f"unexpected request {request.url}")
        step = self.script.pop(0) if len(self.script) > 1 else self.script[0]
        if isinstance(step, Exception):
            raise step
        if callable(step):
            return step(request)
        return FetchResponse(
            request=request,
            url=request.url,
            status=step.status,
            body=step.body,
            headers=step.headers,
            fetch_mode=step.fetch_mode,
            fetched_at=step.fetched_at,
            elapsed_ms=step.elapsed_ms,
        )


def robots_gate(content: str | None = "User-agent: *\nAllow: /", status: int = 200) -> RobotsGate:
    async def fetch(url: str) -> tuple[int, str]:
        return status, content or ""

    return RobotsGate(agent_token="MoSPI-SAFAR-Bot", user_agent="MoSPI-SAFAR-Bot/1.0", fetch=fetch)


async def no_sleep(_: float) -> None:
    return None
