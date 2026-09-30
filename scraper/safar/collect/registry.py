"""
Source registry + the daily sweep.

`run_sweep()` is what the 05:00 IST cron calls. It walks the registry, honours
robots.txt and the per-host rate limits, collects raw quotes, hands them to the
cleaning pipeline and writes the resulting PSI cells to the warehouse. The
counterpart in the web app is `convex/pipeline.ts::runSweep`.
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from datetime import date, datetime, timezone

from ..clean import clean_quotes
from ..index import build_index, load_base, monthly_series, route_contribution
from .base import ScraplingFetcher, RawQuote, SourceAdapter, SweepResult
from .indigo import IndiGoAdapter, MakeMyTripAdapter
from ..db import init_db, insert_raw_quotes, insert_std_prices, insert_index_point

log = logging.getLogger("safar.sweep")
IST = timezone.utc  # swap for zoneinfo.ZoneInfo("Asia/Kolkata") in production

BASKET = [
    ("DEL", "BOM"), ("DEL", "BLR"), ("DEL", "HYD"), ("BOM", "BLR"), ("DEL", "CCU"),
    ("BLR", "HYD"), ("MAA", "DEL"), ("BLR", "COK"), ("DEL", "JAI"), ("HYD", "BOM"),
    ("DEL", "COK"), ("DEL", "PNQ"), ("DEL", "TRV"), ("CCU", "BLR"), ("DEL", "IXC"),
    ("BLR", "MAA"), ("BOM", "CCU"), ("HYD", "CCU"), ("BOM", "GOI"), ("PNQ", "BLR"),
    ("CCU", "PNQ"), ("DEL", "VNS"), ("IDR", "DEL"), ("DEL", "LKO"),
]
LEAD_TIMES = (1, 7, 15, 30, 45)


def registry() -> list[SourceAdapter]:
    """Adapters are added here; selectors live in each module."""
    return [
        IndiGoAdapter(),
        MakeMyTripAdapter(),
        # AirIndiaAdapter(), AkasaAdapter(), SpiceJetAdapter(), AiaExpressAdapter(),
        # YatraAdapter(), EaseMyTripAdapter(), CleartripAdapter(), IxigoAdapter(),
    ]


async def sweep_source(
    adapter: SourceAdapter, fetcher: ScraplingFetcher, day: date
) -> SweepResult:
    started = time.perf_counter()
    collected_at = datetime.now(IST).isoformat()
    quotes: list[RawQuote] = []
    errors = retries = blocks = requests = 0

    # robots.txt is re-read per run: policies change without notice.
    adapter.robots.refresh()

    for origin, destination in BASKET:
        route_id = f"{origin}-{destination}"
        for lead in LEAD_TIMES:
            depart = day + __import__("datetime").timedelta(days=lead)
            url = adapter.build_url(origin, destination, depart)
            if not adapter.robots.allowed(url):
                log.warning("robots.txt disallows %s — skipping", url)
                continue
            await adapter.bucket.acquire()
            delay = adapter.robots.crawl_delay(url) or adapter.crawl_delay
            if delay and delay > adapter.crawl_delay:
                await asyncio.sleep(delay)

            page, status, challenge = await fetcher.fetch(adapter.endpoint.split("/")[0] + ".com", url)
            requests += 1
            if challenge:
                # Never bypass. Record the block and move on — the cell will be
                # imputed downstream and flagged in the coverage report.
                blocks += 1
                continue
            if status >= 500:
                errors += 1
                for backoff in (5, 20, 60):  # bounded retry, then give up
                    retries += 1
                    await asyncio.sleep(backoff)
                    page, status, challenge = await fetcher.fetch(
                        adapter.endpoint.split("/")[0] + ".com", url
                    )
                    requests += 1
                    if not challenge and status < 500:
                        break
            if status >= 400:
                continue

            quotes.extend(
                adapter.parse(
                    page,
                    {
                        "route_id": route_id,
                        "origin": origin,
                        "destination": destination,
                        "day": day,
                        "lead": lead,
                        "collected_at": collected_at,
                    },
                )
            )

    status = "blocked" if blocks > len(BASKET) * len(LEAD_TIMES) * 0.5 else ("degraded" if blocks or errors else "ok")
    return SweepResult(
        source_id=adapter.source_id,
        status=status,
        started_at=collected_at,
        duration_ms=int((time.perf_counter() - started) * 1000),
        requests=requests,
        raw_quotes=len(quotes),
        http_errors=errors,
        retries=retries,
        block_events=blocks,
        robots_allowed=True,
        notes=f"{len(quotes)} quotes · {blocks} blocked cells recorded and imputed",
        quotes=quotes,
    )


async def run_sweep(day: date | None = None) -> dict:
    day = day or datetime.now(IST).date()
    init_db()
    fetcher = ScraplingFetcher()
    await fetcher.start()
    try:
        results = await asyncio.gather(*(sweep_source(a, fetcher, day) for a in registry()))
    finally:
        await fetcher.stop()

    all_quotes: list[RawQuote] = [q for r in results for q in r.quotes]
    insert_raw_quotes(all_quotes)
    
    cleaned, report = clean_quotes(all_quotes)
    insert_std_prices(cleaned, day.isoformat(), datetime.now(IST).isoformat())
    
    reference = load_base(cleaned)  # fixed reference period, stored once
    index_point = build_index(cleaned, day, reference)
    insert_index_point(index_point)

    audit = [
        {
            "sourceId": r.source_id,
            "status": r.status,
            "requests": r.requests,
            "rawQuotes": r.raw_quotes,
            "blockEvents": r.block_events,
            "durationMs": r.duration_ms,
        }
        for r in results
    ]
    log.info("sweep %s: %s raw → %s clean · APIx %s", day, report["rawCount"], report["keptCount"], index_point["value"])

    return {
        "date": day.isoformat(),
        "raw_quotes": report["rawCount"],
        "clean_quotes": report["keptCount"],
        "coverage_pct": report["coverage"],
        "index": index_point,
        "contributions": route_contribution(cleaned, reference),
        "audit": audit,
        "series": monthly_series(),
    }


if __name__ == "__main__":  # 05:00 IST cron entry point
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    print(json.dumps(asyncio.run(run_sweep()), indent=2, default=str))
