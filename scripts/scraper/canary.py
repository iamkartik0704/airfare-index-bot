"""Nightly live parser canary (doc 14 "Regression Detection").

For every *runnable* live source (enabled and ToS-reviewed), runs a handful of
governed searches and checks that the adapter still parses them. Exits 1 if
any source fails to parse, so a cron job or scheduled CI workflow can alert
the team before the main sweep is affected. Never runs in the unit-test CI.

    python -m scripts.scraper.canary [--samples 5]
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from datetime import date, timedelta

from packages.config.reference import get_reference_data
from packages.config.settings import get_settings
from packages.domain.enums import SourceKind
from packages.domain.models.job import ScrapeContext
from packages.scraping.core.exceptions import ParseError
from packages.scraping.engine import ScrapeExecutor
from packages.scraping.fetchers import FetcherFactory
from packages.scraping.sources.registry import build_adapter, runnable_sources


async def run(samples: int) -> int:
    settings = get_settings()
    reference = get_reference_data()
    routes = reference.basket.routes[:samples]
    windows = settings.scheduler.purchase_windows
    fetchers = FetcherFactory(settings.scraping)
    executor = ScrapeExecutor(fetchers, settings.scraping)
    report: dict[str, dict[str, int]] = {}
    failed = False
    try:
        for source in runnable_sources(reference, settings):
            if source.kind is SourceKind.SIMULATED:
                continue
            adapter = build_adapter(source)
            stats = {"ok": 0, "parse_errors": 0, "other_errors": 0, "quotes": 0}
            for i, route in enumerate(routes):
                window = windows[i % len(windows)]
                context = ScrapeContext(
                    source_id=source.id,
                    origin=route.origin,
                    destination=route.destination,
                    travel_date=date.today() + timedelta(days=window),
                    purchase_window=window,
                    observation_date=date.today(),
                )
                outcome = await executor.execute(adapter, context)
                if outcome.error is None:
                    stats["ok"] += 1
                    stats["quotes"] += len(outcome.quotes)
                elif isinstance(outcome.error, ParseError):
                    stats["parse_errors"] += 1
                else:
                    stats["other_errors"] += 1
            failed = failed or stats["parse_errors"] > 0
            report[source.id] = stats
    finally:
        await fetchers.aclose()
    print(json.dumps(report, indent=2))
    if not report:
        print("no runnable live sources (enable + review ToS in sources.yaml)", file=sys.stderr)
    return 1 if failed else 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--samples", type=int, default=5)
    return asyncio.run(run(parser.parse_args().samples))


if __name__ == "__main__":
    raise SystemExit(main())
