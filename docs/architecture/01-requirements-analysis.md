# 01 Requirements Analysis

## Overview
This document analyzes the requirements derived from the official SIH 2026 Problem Statement 26056 for the Airfare Price Index (APIx) project. The solution must support automated scraping of airline and OTA websites, data normalization, database storage, index computation, and visualization via a dashboard.

## Requirements Matrix

| Requirement | Why it exists | Subsystem responsible | Implementation approach | Priority | Prototype vs Production |
| --- | --- | --- | --- | --- | --- |
| **Web-scraping engine** | Essential for automated price collection | Scraping Engine | Playwright/HTTP clients, adapter pattern for each source | High | Both |
| **Handle JS-rendered pages** | Many modern airline/OTA sites use SPAs (React/Angular) | Scraping Engine (Browser Fetcher) | Playwright to intercept XHR/JSON responses | High | Both |
| **Multiple source support** | IndiGo, Air India, Akasa, MakeMyTrip, Yatra, etc. | Source Adapters | Standardized `BaseFetcher` and parsing interfaces | High | Proto: 2-3, Prod: All |
| **Purchase windows (T+1, T+7, T+15, T+30, T+45)** | Dynamic pricing is heavily dependent on lead time | Orchestration & Scraper | Parameterized scraping jobs across dates | High | Both |
| **Route basket based on DGCA** | NSO needs representative city-pairs | Index Engine & Orchestration | Configuration driven by DGCA data | High | Both |
| **Fare breakdown (base, tax, fee)** | CPI needs granular component analysis | Parser & Data Pipeline | Extraction logic per source | High | Both |
| **Handle cancellations & sold-out** | Missing data impacts index stability | Scraping Engine & Pipeline | Flag as `UNAVAILABLE` in normalized db | Medium | Both |
| **Ethical scraping & rate limiting** | Prevent DOS, avoid IP bans, comply with terms | Scraper (Rate Limiter) | Exponential backoff, delays, respect robots.txt | High | Both |
| **Data deduplication** | Same flight from airline vs OTA needs resolution | Data Pipeline (ETL) | Unique constraints on carrier+flight+date | High | Both |
| **Index Construction Module** | The core business value for NSO/MoSPI | Index Engine | Daily/Weekly/Monthly aggregations | High | Both |
| **Dashboard & Visualizations** | Visualize trends, heatmaps, lead-time elasticity | Frontend (React/Next.js) | Recharts, DeckGL for heatmaps | High | Both |
| **30-day Backtesting** | Validate the model against DGCA public data | Testing / Index Engine | Automated scripts to compare historical trends | Medium | Prototype |
| **API for NSO/RBI** | Downstream consumption by govt bodies | API Layer (FastAPI) | RESTful JSON endpoints | High | Both |

## Specific Edge Cases
1. **Dynamic Pricing Volatility:** Fares change by 200-400% daily. The job scheduler must run multiple intra-day sweeps and average them or take the median for the daily quote.
2. **Missing/Quarantined Data:** If a parser fails due to DOM changes, the pipeline must flag the run, fall back to previous quotes if applicable, or quarantine the source.
3. **Outlier Detection:** Erroneous parsed prices (e.g., ₹100 instead of ₹10,000) must be detected via standard deviation checks and quarantined.
