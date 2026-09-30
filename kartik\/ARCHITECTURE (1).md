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
windows, published daily through a robust FastAPI endpoint that the NSO and RBI can consume.

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
│              Python Scraper sweeps at 05:00 IST                              │
└───────────────┬─────────────────────────────────────────────────────────────┘
┌───────────────▼─────────────────────────────────────────────────────────────┐
│ CLEANING     currency parse · de-duplication · sold-out/cancelled drop ·    │
│              MAD outlier rejection · base/tax/UDF/fee decomposition ·        │
│              flagged imputation of blocked cells                             │
└───────────────┬─────────────────────────────────────────────────────────────┘
┌───────────────▼─────────────────────────────────────────────────────────────┐
│ DATABASE     DuckDB embedded OLAP database (`data/apix.duckdb`)             │
│              Millions of rows aggregated instantaneously                     │
└───────────────┬─────────────────────────────────────────────────────────────┘
┌───────────────▼─────────────────────────────────────────────────────────────┐
│ INDEX ENGINE FastAPI backend running fixed-basket Laspeyres estimators,      │
│              DGCA weights, hedonic quality divisors, and covariates          │
└───────────────┬─────────────────────────────────────────────────────────────┘
┌───────────────▼─────────────────────────────────────────────────────────────┐
│ DELIVERY     React/Vite Dashboard (Neobrutalist UI) & JSON REST APIs         │
│              Sub-group tracking, elasticity curves, and back-tests           │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 3.1 Repository map

| Path | Role |
|---|---|
| `scraper/safar/collect/base.py` | Adapter contract, robots gate, token bucket, Playwright fetcher |
| `scraper/safar/collect/indigo.py` | Reference airline + OTA adapters (selectors, URL building, parsing) |
| `scraper/safar/collect/registry.py` | Source registry and the automated sweep |
| `scraper/seed_db.py` | Seeds the initial DuckDB database with generated simulation data |
| `api/main.py` | FastAPI backend exposing REST endpoints for the dashboard |
| `data/apix.duckdb` | Embedded DuckDB database for lightning-fast analytical queries |
| `src/components/neo.tsx` | Core Neobrutalist UI design system components |
| `src/hooks/useApi.ts` | Frontend data-fetching layer with client-side caching |
| `src/pages/*.tsx` | Dashboard views (Overview, Validation, Drivers, etc.) |

### 3.2 Why the demo uses mixed data

The console runs a **deterministic twin** of the market to ensure the application has data to show even when the real-world APIs rate-limit us. The embedded DuckDB is seeded with a 400-day mock history (`seed_db.py`) to demonstrate a reproducible index, seasonality, and back-testing without hammering external servers during a demo. 

Running the Python scraper (`python -m safar.collect.registry`) seamlessly injects live market data into the DuckDB instance alongside the simulated history. The dashboard explicitly badges any charts using simulation data as "Simulated Data" to maintain statistical integrity.

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
  bypass, no purchase flow ever touched.

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
| **Now (prototype)** | FastAPI + DuckDB backend, Playwright scraper, full dashboard console, 12-month back-test |
| **Phase 2** | Production Scrapy cluster, TimescaleDB warehouse, real DGCA reconciliation feed |
| **Phase 3** | NSO pilot: publish APIx as a T&C sub-group alongside the manual series for two quarters |
| **Phase 4** | RBI briefing layer: fuel / rupee pass-through attribution on demand |

---

## 9. Running it

```bash
# Terminal 1: Run the FastAPI backend (Port 8001)
cd api
python main.py

# Terminal 2: Run the Vite React dashboard (Port 5174)
npm install
npm run dev -- --port 5174

# Terminal 3: Run a live data collection sweep
cd scraper
python -m safar.collect.registry
```
