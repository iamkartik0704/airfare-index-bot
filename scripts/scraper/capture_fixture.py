"""Capture a genuine source response as a parser fixture (doc 14).

Runs ONE governed request (robots.txt, rate limit, block detection — the same
path as production) and saves the body under ``tests/fixtures`` so parser
tests can use a real payload instead of a modelled one. It refuses sources
whose terms of service have not been reviewed unless the operator explicitly
confirms the review with ``--tos-reviewed``. It never bypasses a block.

    python -m scripts.scraper.capture_fixture --source indigo --route DEL-BOM \
        --travel-date 2026-10-07 [--tos-reviewed]
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from datetime import date

from packages.config.reference import get_reference_data
from packages.config.settings import REPO_ROOT, get_settings
from packages.domain.models.job import ScrapeContext
from packages.scraping.engine import ScrapeExecutor
from packages.scraping.fetchers import FetcherFactory
from packages.scraping.sources.registry import build_adapter


async def capture(source_id: str, route: str, travel_date: date, tos_reviewed: bool) -> int:
    reference = get_reference_data()
    definition = reference.source(source_id)
    if definition.is_synthetic:
        print("the simulator needs no captures", file=sys.stderr)
        return 2
    if not (definition.tos_reviewed or tos_reviewed):
        print(
            f"{source_id}: terms of service not reviewed; review them and pass --tos-reviewed",
            file=sys.stderr,
        )
        return 2
    origin, destination = route.split("-")
    today = date.today()
    context = ScrapeContext(
        source_id=source_id,
        origin=origin,
        destination=destination,
        travel_date=travel_date,
        purchase_window=max(0, (travel_date - today).days),
        observation_date=today,
    )
    settings = get_settings()
    fetchers = FetcherFactory(settings.scraping)
    try:
        outcome = await ScrapeExecutor(fetchers, settings.scraping).execute(
            build_adapter(definition), context
        )
    finally:
        await fetchers.aclose()
    for response in outcome.responses:
        kind = "json" if "json" in (response.content_type or "") else "html"
        folder = REPO_ROOT / "tests" / "fixtures" / kind / source_id
        folder.mkdir(parents=True, exist_ok=True)
        path = folder / f"captured_{route}_{travel_date.isoformat()}.{kind}"
        path.write_bytes(response.body)
        print(f"saved HTTP {response.status} ({len(response.body)} bytes) → {path}")
    if outcome.error is not None:
        print(f"capture did not succeed: [{outcome.error.code}] {outcome.error}", file=sys.stderr)
        return 1
    print(f"parser extracted {len(outcome.quotes)} quotes from the capture")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--source", required=True)
    parser.add_argument("--route", required=True, help="e.g. DEL-BOM")
    parser.add_argument("--travel-date", required=True, type=date.fromisoformat)
    parser.add_argument("--tos-reviewed", action="store_true")
    args = parser.parse_args()
    return asyncio.run(capture(args.source, args.route, args.travel_date, args.tos_reviewed))


if __name__ == "__main__":
    raise SystemExit(main())
