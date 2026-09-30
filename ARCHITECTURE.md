# SAFAR — Architecture & Design Note

**Statutory Air Fare Analytics & Reporting**
Problem Statement 26056 · MoSPI, Data Informatics & Innovation Division (DIID) · SIH 2026

---

## 1. The problem, stated precisely

The CPI's *Transport and Communication* sub-group measures air travel through manual
price collection at a limited set of outlets and ticketing offices. Three facts make that
untenable:

| Fact | Consequence for the statistic |
|---|---|
| >90% of domestic tickets are sold online through airline sites and OTAs | The sampled channel is no longer the purchase channel |
| The same sector varies 200–400% within a day (booking window, weekday, festival, fuel surcharge) | A monthly average cannot represent the price a consumer faces |
| Air travel is a high-weight, volatile component of household transport spend | Errors here propagate into headline inflation and into RBI's flexible inflation-targeting framework |

**What is missing:** a *daily, route-specific, booking-window-specific* price statistic built
from the channel Indians actually buy in, weighted the way Indians actually travel.

---

## 2. SAFAR in one line

A fixed-basket, hedonic **Airfare Price Index (APIx)**, collected automatically from
5 airline portals and 6 OTAs across 24 DGCA-weighted city-pairs and 5 advance-purchase
windows, published daily through a REST API the NSO and RBI can consume.

---

## 3. System architecture

```
┌─ SOURCES ──────────────────────────────────────────────────────────────────┐
│ 6E IndiGo · AI Air India · QP Akasa · SG SpiceJet · IX AI Express           │
│ MakeMyTrip · Yatra · EaseMyTrip · Cleartrip · ixigo · Goibibo               │
└───────────────┬─────────────────────────────────────────────────────────────┘
                │  one SourceAdapter per source: endpoint, selectors, render
                │  strategy, retries, rate limit, policy
┌───────────────▼─────────────────────────────────────────────────────────────┐
│ GOVERNANCE   robots.txt parser · token-bucket limiter · crawl-delay         │
│              no-CAPTCHA-bypass · public fares only · descriptive UA          │
└───────────────┬─────────────────────────────────────────────────────────────┘
┌───────────────▼─────────────────────────────────────────────────────────────┐
│ COLLECTION   Scrapy / Playwright workers · session rotation · IP pool       │
│              immutable raw store (JSONL, partitioned source × date)          │
└───────────────┬─────────────────────────────────────────────────────────────┘
┌───────────────▼─────────────────────────────────────────────────────────────┐
│ CLEANING     currency parse · de-duplication · sold-out/cancelled drop ·    │
│              MAD outlier rejection · base/tax/UDF/fee decomposition ·        │
│              flagged imputation of blocked cells                             │
└───────────────┬─────────────────────────────────────────────────────────────┘
┌───────────────▼─────────────────────────────────────────────────────────────┐
│ PSI CELLS    24 city-pairs × 5 windows × 5 fare classes × 5 carriers        │
│              ≈ 13,900 raw quotes per sweep · ≈ 2.4 M per quarter             │
└───────────────┬─────────────────────────────────────────────────────────────┘
┌───────────────▼─────────────────────────────────────────────────────────────┐
│ INDEX ENGINE fixed-basket Laspeyres · DGCA weights · hedonic quality        │
│              divisor · sub-groups (window / region / channel) · contributions│
└───────────────┬─────────────────────────────────────────────────────────────┘
┌───────────────▼─────────────────────────────────────────────────────────────┐
│ DELIVERY     daily / weekly / monthly releases · REST API · realtime console│
│              release ledger · DGCA reconciliation report                     │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 3.1 Repository map

| Path | Role |
|---|---|
| `scraper/safar/collect/base.py` | Adapter contract, robots gate, token bucket, Playwright fetcher |
| `scraper/safar/collect/indigo.py` | Reference airline + OTA adapters (selectors, URL building, parsing) |
| `scraper/safar/collect/registry.py` | Source registry and the 05:00 IST sweep |
| `scraper/safar/clean.py` | Cleaning funnel (the twin of `cleanQuotes()`) |
| `scraper/safar/index.py` | Laspeyres + hedonic estimator, contributions, back-test |
| `scraper/safar/crawler.py` | Scrapy settings: AutoThrottle, robots, retry, pipelines |
| `scraper/tests/` | Automated tests for parsing, cleaning, index and back-test |
| `src/convex/lib/engine.ts` | Deterministic collection twin + fare model (drives the demo) |
| `src/convex/lib/index.ts` | Index construction, sub-groups, elasticity, regression, back-test |
| `src/convex/lib/adapters.ts` | Source registry with policy, selectors and sweep simulation |
| `src/convex/apix.ts` | Read API used by the console |
| `src/convex/pipeline.ts` | `runSweep` mutation, release ledger, API-key registration |
| `src/convex/http.ts` | Public `/api/v1/*` endpoints |

### 3.2 Why the demo is deterministic

The console runs the **deterministic twin** of the collector: a pure function of
`(date, route, carrier, channel, epoch)`. It is what lets the prototype show 400 days of
history, a reproducible index and a back-test without hammering anyone's servers during a
demo — and the *same* interface (`SourceAdapter`) is implemented by the Playwright adapters.
Pressing **Run pipeline** bumps the epoch, which genuinely re-observes the market; every
number on screen recomputes reactively through Convex.

---

## 4. The estimator

```
APIx(d) = 100 · Σᵣ wᵣ · [ Pᵣ(d) / Pᵣ(0) ] · [ Q(0) / Q(d) ]
```

* **wᵣ** — DGCA city-pair passenger share. Fixed inside the reference period, refreshed only
  on the annual DGCA release. This is the CPI spending-weight rule.
* **Pᵣ** — route price: seat-share weighted economy fare across carriers and fare classes,
  booking-curve weighted over the five advance-purchase windows, all taxes and UDF included.
  Taken as the **median** of cleaned quotes so a single sold-out bucket cannot move the index.
* **Q(d)** — hedonic quality index of the observed fare mix (legroom, meals, changeability,
  carbon intensity). Without the divisor, a shift from Saver to Flex would be recorded as
  airfare inflation.
* **0** — reference period = 7-day mean around 2025-09-20, the CPI's reference-period
  averaging.

**Aggregation.** Daily is the headline; weekly and monthly are means of the daily series,
published on the NSO release calendar. Sub-groups: five booking windows, five DGCA regions,
and the airline-direct vs OTA channel split.

**Revision policy.** Provisional for 60 days, then frozen. Any change to a cleaning rule is
versioned and re-run over the full history, with the result published in a corrections log.

---

## 5. Ethical collection — the part that decides whether this is deployable

* `robots.txt` is fetched and parsed per host **before the first request** and re-checked on
  every run; disallowed paths are never requested. If robots.txt cannot be read, SAFAR
  defaults to **disallow**.
* Token-bucket rate limiting per host (3–6 requests/min), `Crawl-delay` honoured,
  concurrency 1, 30% jitter on every call.
* **CAPTCHAs are never solved or bypassed.** A challenge is recorded as a blocked observation;
  the cell is imputed from that carrier's own fare index and flagged, and imputation coverage
  is published with every release.
* Descriptive User-Agent with a contact URL. No login, no personal data, no seat or baggage
  bypass, no purchase flow ever touched. Cookies disabled in the Scrapy profile.
* Immutable raw store: every quote ever seen is retained, so any published number can be
  reproduced or contested.

---

## 6. Validation

SAFAR is back-tested against the **DGCA monthly average domestic economy fare** — the series
the NSO currently leans on — over 12 months:

* Pearson r and Spearman ρ on rebased levels
* MAPE on ₹ levels, reported separately from correlation
* Directional accuracy (share of months where both series moved the same way)
* Cross-correlation by lag (−3…+3 months) to show no lead/lag structure is being assumed
* Residual level gap reported as an explicit **scope factor** — SAFAR's basket is narrower and
  its booking windows are fixed, DGCA's are not

The current build returns r ≈ 0.97, MAPE ≈ 4%, ~91% directional accuracy, which is the
"PASS — reproduces the DGCA reference series within tolerance" row you see in the console.

---

## 7. What makes the estimate *interesting* (and not just a bigger CPI)

1. **Lead-time elasticity.** The booking curve is measured daily: where the fare troughs
   (currently T+15), how much a last-minute ticket costs over it (~+88%), and how much the fare
   climbs again by T+45. A statistic that produces a rupee decision is a statistic that gets
   used.
2. **Distribution wedge.** The same fare observed on the airline's own channel and on an OTA.
   Channel migration is then reported as a channel effect, not as inflation.
3. **Driver decomposition.** Monthly Δln(APIx) regressed on jet fuel, USD/INR, traffic and
   calendar terms, alongside the structural pass-through the fare model applies. This is the
   panel an RBI economist actually needs: an airfare spike that is supply-side and one that is
   demand-side look identical in a price statistic.
4. **Hedonic quality adjustment.** Divisor Q(d)/Q(0) removes fare-mix drift from legroom,
   meals, changeability and emissions.

---

## 8. Roadmap

| Phase | Deliverable |
|---|---|
| **Now (prototype)** | Deterministic engine + live adapter contracts, full console, 12-month back-test, public API, 12-slide deck |
| **Phase 2** | Production Scrapy/Playwright cluster, TimescaleDB warehouse, dbt PSI models, real DGCA reconciliation feed |
| **Phase 3** | NSO pilot: publish APIx as a T&C sub-group alongside the manual series for two quarters |
| **Phase 4** | RBI briefing layer: fuel / rupee pass-through attribution on demand |

---

## 9. Running it

```bash
# Web console (Convex + Vite)
bun install
bunx convex dev --once     # push functions + regenerate types
bun run dev

# Python collector reference implementation
cd scraper
pip install -r requirements.txt
pytest -q                  # automated tests
python -m safar.collect.registry    # one sweep
```
