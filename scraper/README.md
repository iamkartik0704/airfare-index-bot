# SAFAR collector — Python reference implementation

The production half of SAFAR: multi-source, ethically rate-limited collection of publicly
displayed airfares, a cleaning funnel, and the index estimator. It is a line-for-line twin of
the TypeScript engine in `src/convex/lib/` — same interface, same cleaning rules, same
estimator — so either side can be swapped for the other without touching anything downstream.

```bash
pip install -r requirements.txt
playwright install chromium

pytest -q                        # automated tests: parsing, cleaning, index, back-test
python -m safar.collect.registry # one sweep → clean → index → audit trail
```

Cron: `5 5 * * *  cd scraper && python -m safar.collect.registry >> /var/log/safar.log`

## Layout

| File | Responsibility |
|---|---|
| `safar/collect/base.py` | `SourceAdapter` contract, `RawQuote`, robots gate, token bucket, Playwright fetcher |
| `safar/collect/indigo.py` | Reference airline (IndiGo) and OTA (MakeMyTrip) adapters |
| `safar/collect/registry.py` | Source registry, per-source sweep, daily entry point |
| `safar/clean.py` | Cleaning funnel: parse → dedupe → drop → MAD outliers → decompose → impute |
| `safar/index.py` | Fixed-basket Laspeyres + hedonic divisor, sub-groups, contributions, back-test |
| `safar/crawler.py` | Scrapy project settings (AutoThrottle, robots, retry, pipelines) |
| `tests/test_pipeline.py` | pytest suite |

## Adding a source

1. Create `safar/collect/<name>.py` with a `SourceAdapter` subclass: `build_url()` and
   `parse()`.
2. Append an instance to `registry()`.
3. Set its selectors to the **public** fare markup only. Never add a checkout, login or
   payment path — `ALLOWED_PATHS` in `crawler.py` is checked in review.

Nothing else changes: cleaning, indexing and publishing are source-agnostic.

## Compliance guarantees (enforced in code, not by discipline)

* `RobotsGate` parses `robots.txt` per host, honours `Crawl-delay`, and **defaults to
  disallow** when robots.txt cannot be read.
* `TokenBucket` enforces 3–6 requests/min per host, concurrency 1, jitter on every call.
* Challenge pages (`captcha`, `unusual traffic`, `cf-challenge`, …) are **never bypassed**:
  the cell is logged as blocked and imputed downstream with a flag.
* Descriptive User-Agent with a contact URL; cookies disabled; no personal data, no purchase
  flow, no seat or baggage bypass.
* Every sweep writes an immutable audit row per source: status, requests, raw quotes, blocks,
  retries, duration.

## Index, in one line

```
APIx(d) = 100 · Σᵣ wᵣ · [Pᵣ(d)/Pᵣ(0)] · [Q(0)/Q(d)]
```

`wᵣ` DGCA city-pair passenger share · `Pᵣ` booking-curve weighted median economy fare,
all taxes · `Q(d)` hedonic quality of the observed fare mix · `0` stored reference snapshot
(`safar/data/base_snapshot.json`), seeded once and then fixed.
