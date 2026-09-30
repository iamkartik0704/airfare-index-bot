# Implementation Roadmap

## Stage 0: Repository Foundation
- Scaffold monorepo (`apps/`, `packages/`).
- Setup CI/CD linting and database Docker containers.

## Stage 1: Canonical Domain Models
- Define `AirfareQuote` and `ScrapeJob` in SQLAlchemy and Pydantic.

## Stage 2: Scraping Core
- Implement `BaseFetcher`, `BrowserFetcher`, and the `Governance` rate-limiter.

## Stage 3: First Airline Integration
- Build the `IndiGo` adapter. Capture HTML/XHR fixtures and write unit tests.

## Stage 4: Raw Storage & Normalization
- Implement the JSONB insertion and the ETL pipeline to output to canonical tables.

## Stage 5: Scheduling
- Implement Celery/Redis (or APScheduler) to trigger Stage 3 code automatically.

## Stage 6: Index Engine
- Implement the Laspeyres index logic and LOCF imputation.

## Stage 7: API & Dashboard
- Build FastAPI endpoints. Wire up the React dashboard.

## Stage 8: Additional Sources
- Scale horizontally by adding Air India, MMT, Yatra, etc.

## Stage 9: Backtesting & Validation
- Run historical data. Reconcile against DGCA averages.
