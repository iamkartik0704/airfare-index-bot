# SAFAR — Statutory Air Fare Analytics & Reporting

**Real-time Airfare Price Index (APIx) for India** · Problem Statement 26056 · MoSPI (DIID) · SIH 2026

A fixed-basket, hedonic airfare price index built by automatically collecting fares from
5 airline portals and 6 OTAs across 24 DGCA-weighted city-pairs and 5 advance-purchase
windows, engineered to augment the *Transport and Communication* sub-group of the CPI.

```
APIx(d) = 100 · Σᵣ wᵣ · [Pᵣ(d)/Pᵣ(0)] · [Q(0)/Q(d)]
```

* **`wᵣ`** DGCA city-pair passenger share, fixed in the reference period (the CPI spending-weight rule)
* **`Pᵣ`** booking-curve weighted median economy fare, all taxes and UDF, five booking windows
* **`Q(d)`** hedonic quality of the observed fare mix (legroom, meals, changeability, CO₂)
* **`0`** stored reference snapshot, seeded once and then fixed

## What's in the box

| Piece | Where |
|---|---|
| FastAPI Backend & Database API | `api/main.py` |
| Local Embedded Database | `data/apix.duckdb` (DuckDB) |
| Python Scrapy/Playwright collector | `scraper/` |
| Dashboard UI Components | `src/components/` |
| Dashboard Pages & Routing | `src/pages/` |
| Custom Neobrutalist UI System | `src/index.css` & `src/components/neo.tsx` |
| Full design note + PPT speaker notes | `ARCHITECTURE.md` |

## Console pages

`/dashboard` index · `sectors` heat-map & contributions · `leadtime` booking curve ·
`drivers` fuel/rupee/traffic decomposition · `pipeline` collector audit & compliance ·
`explorer` raw → cleaned quotes · `validation` DGCA back-test · `methodology` PSI doc ·
`api` endpoint reference · `deck` 12-slide presentation, live from the data.

## Public API

```bash
curl -s "http://localhost:8001/api/index"
```

Endpoints: `/api/index`, `/api/routes/heatmap`, `/api/elasticity`, `/api/channelAnalysis`, `/api/pipelineState`, `/api/validation`, `/api/drivers`, `/api/methodology`.

## Running Local Environment

The project is split into a FastAPI backend and a Vite React frontend.

```bash
# Terminal 1: run the FastAPI backend (Port 8001)
cd api
python main.py

# Terminal 2: run the Vite React dashboard (Port 5174)
npm install
npm run dev -- --port 5174
```

## Data Origin Caveats

> [!WARNING]
> The current index uses **synthetic/simulated data** for demonstration purposes. A 400-day mock series and mock prices are injected to demonstrate the methodology and the API's capabilities. 
> 
> * Any charts or data showing synthetic rows will have a "Simulated data" badge.
> * The **Validation** dashboard uses a real, static export of the official MoSPI CPI dataset (`data/esankhyiki-airfare-cpi.json`). The FastAPI backend calculates real Pearson and Spearman correlations against the DuckDB index points using Pandas/Numpy. We use a static JSON reference rather than a live fetcher due to government API auth barriers.
> * The **Drivers** dashboard performs real Multiple Linear Regression (OLS) on the backend using `numpy.linalg.lstsq`.
> * To get live data, you must run the scraper sweep manually (`cd scraper && python -m safar.collect.registry`), which will mark the newly fetched rows as live data.

## Design principles

1. **Statutory by construction** — the same estimator family, basket discipline and sub-group
   reporting the CPI uses, so SAFAR can be adopted rather than admired.
2. **Ethical by construction** — robots.txt is parsed per host and re-checked every run,
   rate limits are code defaults, and CAPTCHAs are never bypassed: a challenge is logged and
   the cell is imputed and flagged.
3. **Reproducible** — the demo engine is a pure function of (date, route, carrier, channel,
   epoch); every number on screen can be regenerated from the seed.
