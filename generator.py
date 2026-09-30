import os
import textwrap

folders = [
    "apps/api/routers",
    "apps/api/services",
    "apps/api/repositories",
    "apps/api/schemas",
    "apps/dashboard/src/components",
    "apps/dashboard/src/pages",
    "packages/scraping/sources/airlines/indigo",
    "packages/scraping/sources/airlines/air_india",
    "packages/scraping/sources/airlines/air_india_express",
    "packages/scraping/sources/airlines/akasa",
    "packages/scraping/sources/airlines/spicejet",
    "packages/scraping/sources/otas/makemytrip",
    "packages/scraping/sources/otas/ixigo",
    "packages/scraping/sources/otas/cleartrip",
    "packages/scraping/sources/otas/yatra",
    "packages/scraping/sources/otas/easemytrip",
    "packages/scraping/core/fetchers",
    "packages/scraping/core/exceptions",
    "packages/scraping/core/session",
    "packages/domain/models",
    "packages/data_pipeline/cleaning",
    "packages/data_pipeline/normalization",
    "packages/index_engine/methodology",
    "packages/index_engine/weighting",
    "packages/observability/metrics",
    "packages/observability/logging",
    "infrastructure/docker",
    "infrastructure/k8s",
    "infrastructure/db",
    "tests/unit",
    "tests/integration",
    "tests/e2e",
    "tests/fixtures/html",
    "scripts/db",
    "scripts/scraper",
    "docs/architecture",
    "docs/pdf"
]

for folder in folders:
    os.makedirs(folder, exist_ok=True)
    with open(os.path.join(folder, ".gitkeep"), "w") as f:
        f.write("")

# Create some basic python files to establish the skeleton
with open("packages/scraping/core/fetchers/base.py", "w") as f:
    f.write(textwrap.dedent("""\
    class BaseFetcher:
        def fetch(self, request):
            raise NotImplementedError
    """))

with open("packages/scraping/core/fetchers/http.py", "w") as f:
    f.write(textwrap.dedent("""\
    from .base import BaseFetcher
    class HttpFetcher(BaseFetcher):
        def fetch(self, request):
            pass # Implementation
    """))

with open("packages/scraping/core/fetchers/browser.py", "w") as f:
    f.write(textwrap.dedent("""\
    from .base import BaseFetcher
    class BrowserFetcher(BaseFetcher):
        def fetch(self, request):
            pass # Implementation
    """))

with open("packages/domain/models/quote.py", "w") as f:
    f.write(textwrap.dedent("""\
    from pydantic import BaseModel
    from datetime import datetime

    class AirfareQuote(BaseModel):
        source: str
        carrier: str
        flight_number: str
        origin: str
        destination: str
        search_timestamp: datetime
        travel_date: datetime
        advance_purchase_days: int
        base_fare: float
        taxes: float
        total_fare: float
        currency: str
    """))

docs = {
    "00-executive-summary.md": """
# Executive Summary

This document presents the detailed architectural blueprint for the SIH 2026 project (Problem Statement 26056), aiming to build a Real-time Airfare Price Index for India. The goal is to develop an automated web scraping system that gathers data from major Indian airline portals and Online Travel Aggregators (OTAs) and generates a consumer price index for air travel.

## Core Objectives
1. **Data Acquisition:** Reliably scrape airfare quotes from dynamic, JS-rendered web pages while respecting ethical scraping boundaries and site policies.
2. **Data Pipeline:** Clean, normalize, and store airfare quotes to handle anomalies, missing data, and deduplication.
3. **Index Computation:** Calculate daily, weekly, and monthly airfare indices using route weightings analogous to official DGCA/NSO standards.
4. **Dissemination:** Present findings via a dashboard and a robust API designed for potential integration with RBI/NSO workflows.

This V4 architecture eschews unnecessary complexity from earlier iterations (like over-reliance on microservices and Kafka streams where not needed for a prototype) in favor of a robust, modular, and maintainable monolith or modular-monolith approach, using a dedicated scraper core inspired by Scrapling.
    """,
    
    "01-requirements-analysis.md": """
# Requirements Analysis

The Problem Statement (26056) details explicit functional and non-functional requirements.

## Functional Requirements
- **Target Sources:** Must scrape IndiGo, Air India, Air India Express, Akasa Air, SpiceJet, and OTAs (MakeMyTrip, Yatra, EaseMyTrip, Cleartrip, Ixigo, Goibibo).
- **Temporal Windows:** Need quotes for T+1, T+7, T+15, T+30, T+45 advance purchase windows.
- **Route Selection:** Must maintain a basket of city-pairs based on DGCA traffic data (e.g., DEL-BOM, BOM-BLR).
- **Data Extracted:** Must separate base fare, taxes, user development fee (UDF), and convenience charges. Must detect cancellations and sold-out flights.
- **Index Computation:** Calculate daily, weekly, and monthly indices using given routes and weights.
- **Delivery:** Must have an API for RBI/NSO and an interactive web dashboard for visualizations (heatmaps, elasticity curves, price trends).

## Non-Functional Requirements
- **Scraping Compliance:** Must respect `robots.txt`, handle rate-limiting, and practice ethical scraping. Should not use malicious bot-bypass techniques.
- **Resilience:** Needs IP rotation, session management, and robust exception handling.
- **Data Quality:** Must handle missing values, outliers, and deduplication efficiently.
- **Testing & Validation:** Requires documentation, automated testing, and at least 30 days of back-tested results against DGCA public data.
    """,
    
    "02-v3-review.md": """
# V3 Architecture Review

The V3 architecture proposed an over-engineered solution, heavily reliant on microservices, event streaming (Kafka), and complex container orchestration that exceeds the requirements of an SIH prototype.

## Critique & Modifications
- **Kafka & Event Streaming:** *Removed*. The scale of scraping for a few dozen routes a few times a day does not justify Kafka. A Postgres-backed job queue (or Redis/Celery) is sufficient and far easier to deploy.
- **Microservices Sprawl:** *Modified*. We will consolidate the backend into a modular monolith. The scraping engine, data pipeline, and API will reside in well-defined packages within a single repository, making it easier to test and deploy.
- **Scraping Brittleness:** *Modified*. V3 lacked a strong abstraction for source websites. We are introducing the `SourceAdapter` pattern and a custom Fetcher abstraction (inspired by Scrapling) to isolate HTML/network changes from the core processing logic.
- **Raw Data Preservation:** *Added*. V3 did not explicitly mandate storing raw HTML/JSON responses. We must store raw payloads to allow replayability and parser regression testing.
- **Over-engineered Security:** *Modified*. Instead of complex proxy meshes, we will implement simple session management and exponential backoff, adhering to ethical scraping principles.
    """,

    "03-system-architecture.md": """
# System Architecture

The V4 architecture adopts a modular approach to ensure clean separation of concerns.

## Subsystems
1. **Scraping Engine:** A specialized module for fetching raw data from target websites. It supports HTTP and Browser-based fetching, handling sessions and rate limits.
2. **Data Pipeline:** Responsible for validating, normalizing, and cleaning raw responses into canonical `AirfareQuote` models.
3. **Index Engine:** Computes the actual APIx (Airfare Price Index) using the canonical data and configured route weights.
4. **API Layer (FastAPI):** Exposes endpoints for the dashboard and external consumers (NSO/RBI).
5. **Dashboard (React/Vue/Svelte):** Visualizes the data.
6. **Job Orchestrator (APScheduler/Celery):** Manages the execution of scraping jobs based on defined schedules.

## Data Flow
`Job Orchestrator` -> `Scraping Engine` -> `Source Adapter` -> `Raw Response Store` -> `Data Pipeline` (Parser -> Normalizer -> Quality Checks) -> `Canonical DB` -> `Index Engine` -> `API` -> `Dashboard`

This flow guarantees that raw data is never lost, allowing for retroactive parser fixes and re-computation.
    """,

    "04-scraping-engine.md": """
# Scraping Engine

The scraping engine is the heart of the data acquisition process. We eschew heavy frameworks like Scrapy in favor of a custom, Scrapling-inspired engine that is lightweight and tailored to airfare data.

## Core Abstractions
- **BaseFetcher:** Interface for making requests.
- **HttpFetcher:** For APIs and static HTML (uses `httpx` or `requests`).
- **BrowserFetcher:** For JS-heavy sites (uses Playwright).
- **SessionManager:** Handles cookies, user agents, and IP rotation.
- **RetryPolicy:** Exponential backoff for rate limits.
- **RateLimiter:** Enforces per-domain concurrency limits.

## The Fetch Cycle
When a job is dispatched, the engine selects the appropriate fetcher based on the `SourceMetadata`. The fetcher retrieves the content, handling any network-level exceptions or rate limits. The result is returned as a `ScrapeResult` object containing the raw HTML/JSON and metadata (timestamp, source, latency), which is then passed to the source adapter.
    """,

    "05-source-adapters.md": """
# Source Adapters

Each airline and OTA has a dedicated Source Adapter. This isolates website-specific logic from the rest of the application.

## Structure
- `scraping/sources/airlines/indigo/adapter.py`
- `scraping/sources/otas/makemytrip/adapter.py`

## Responsibilities
- **Request Builder:** Constructs the specific URL, headers, and payload required by the source for a given route, date, and passenger count.
- **Parser:** Extracts raw data from the specific HTML or JSON structure of the source.
- **Normalizer:** Maps the raw extracted data into the canonical `AirfareQuote` domain model.

By using adapters, if a website changes its layout, only the parser in its specific adapter needs updating. The rest of the pipeline remains completely untouched.
    """,

    "06-domain-model.md": """
# Canonical Domain Model

The canonical models ensure that downstream systems (pipeline, index engine, API) work with a unified data structure, regardless of the source.

## Key Models (Pydantic / SQLAlchemy)
- **AirfareQuote:** The primary data entity.
  - `source`: (e.g., 'makemytrip', 'indigo')
  - `carrier`: (e.g., '6E', 'AI')
  - `flight_number`: (e.g., '6E-123')
  - `origin`, `destination`: IATA codes.
  - `travel_date`, `search_timestamp`: Datetimes.
  - `advance_purchase_days`: e.g., 1, 7, 15.
  - `base_fare`, `taxes`, `convenience_fee`, `total_fare`: Monetary values.
- **FlightSegment:** For multi-leg journeys.
- **Route:** Represents a city pair and its weighting in the index.
- **IndexObservation:** An aggregated metric for a specific route and window.

These models will be strictly typed and validated upon instantiation to prevent malformed data from entering the database.
    """,

    "07-data-pipeline.md": """
# Data Pipeline

The data pipeline processes raw scraper output into analytical data.

## Stages
1. **Raw Extraction:** The `SourceAdapter` parses the HTML/JSON.
2. **Schema Validation:** The output is validated against the `AirfareQuote` Pydantic model. Invalid records are flagged and quarantined.
3. **Normalization:** Currencies are converted if necessary, and IATA codes are standardized.
4. **Deduplication:** A unique hash is generated based on `source`, `flight_number`, `travel_date`, and `search_timestamp` to prevent duplicate inserts.
5. **Outlier Detection:** Statistical checks (e.g., z-score, IQR) identify implausible fares (e.g., a 100 INR fare or 1,000,000 INR fare), flagging them for review rather than silent deletion.
6. **Storage:** Clean data is inserted into the `normalized_quotes` table.

Raw payloads are stored in an S3 bucket or a local filesystem (with paths stored in DB) to allow re-running the pipeline if parser logic is improved.
    """,

    "08-database-design.md": """
# Database Design

We use PostgreSQL for its robust relational capabilities and JSONB support for unstructured raw data metadata.

## Key Tables
- `sources`: ID, Name, Type (Airline/OTA), Status.
- `routes`: Origin, Destination, Weight (for index calculation).
- `scrape_jobs`: Job ID, Status, Start/End Time.
- `raw_quotes`: ID, Job ID, Raw Payload (JSONB or text), Created At.
- `normalized_quotes`: Primary table for `AirfareQuote` data. 
  - Indexes on: `(travel_date, origin, destination)`, `(search_timestamp)`.
- `index_values`: Computed indices. Date, Period (Daily/Weekly), Value, Route ID (if applicable).
- `source_health`: Metrics on scraper success/failure rates.

Data separation ensures that analytical queries on `normalized_quotes` are fast and unencumbered by massive raw payloads.
    """,

    "09-index-engine.md": """
# Index Engine

The Index Engine is responsible for the statistical computation of the Airfare Price Index (APIx).

## Methodology
The engine will implement a Laspeyres or Fisher price index formula, depending on NSO alignment.
1. **Aggregation:** Fares for a route (e.g., DEL-BOM) across all sources and advance purchase windows are aggregated (median or trimmed mean to reduce volatility).
2. **Weighting:** Each route's aggregate price is multiplied by its traffic weight (sourced from DGCA data).
3. **Base Period Comparison:** The weighted sum is compared against a base period (e.g., Jan 2024) to generate the index value (Base = 100).

## Interfaces
- `RouteWeightCalculator`: Pluggable interface to update weights based on new DGCA data.
- `IndexAggregator`: Handles missing observations (e.g., if a flight is sold out, we carry forward the last known price or interpolate).
    """,

    "10-job-orchestration.md": """
# Job Orchestration

Scheduling and running scraping tasks reliably is critical.

## Implementation
We will use APScheduler integrated within the FastAPI app, backed by PostgreSQL (or Redis) as a job store. This avoids the overhead of Celery for a prototype while providing sufficient reliability.

## Job Matrix
Jobs are generated across these dimensions:
- `Routes`: Top 20-50 city pairs.
- `Purchase Windows`: T+1, T+7, T+15, T+30, T+45.
- `Sources`: 5 Airlines + 5 OTAs.

## Resiliency
- **Timeouts:** Hard limits on fetch requests (e.g., 30s).
- **Retries:** Exponential backoff for 429 (Too Many Requests) or 500 errors.
- **Circuit Breakers:** If a source fails 5 times consecutively, it is disabled for 1 hour, and an alert is logged.
    """,

    "11-api-architecture.md": """
# API Architecture

The backend will be built with FastAPI to provide high-performance, async endpoints.

## Core Endpoints
- `GET /api/v1/index/daily`: Returns the daily APIx values.
- `GET /api/v1/index/historical`: Returns time-series data for the dashboard.
- `GET /api/v1/fares/routes/{origin}/{destination}`: Returns aggregated fares for a specific route.
- `GET /api/v1/system/health`: Source health and scrape success rates.

## Layers
- **Routers:** Handle HTTP requests and responses.
- **Services:** Business logic (e.g., calculating index on-the-fly or fetching precomputed values).
- **Repositories:** Database abstraction (SQLAlchemy or SQLModel).
- **Schemas:** Pydantic models for request/response validation.

Error handling will use standard HTTP status codes and provide actionable JSON error details.
    """,

    "12-dashboard-architecture.md": """
# Dashboard Architecture

The frontend will provide intuitive visualizations of the airfare index and system health.

## Technologies
React (or Vue/Svelte) with a charting library like Recharts or Chart.js.

## Key Views
1. **APIx Overview:** A main chart showing the aggregate Daily/Weekly/Monthly airfare index trend over time.
2. **Sector Heatmap:** A visual representation of price intensity across different routes (e.g., red for high price surges, green for stable/low prices).
3. **Lead-Time Elasticity:** A curve showing how prices change as the travel date approaches (T+45 down to T+1).
4. **Source Health:** A dashboard for administrators to monitor which scrapers are succeeding or failing, allowing quick debugging.
    """,

    "13-observability.md": """
# Observability

Comprehensive observability is crucial for a scraping-based system, as target websites change frequently.

## Strategy
1. **Structured Logging:** All logs will be output in JSON format, containing context like `source`, `route`, and `job_id`.
2. **Metrics:** 
   - Scrape Success/Failure rates.
   - HTTP Status Code distributions.
   - Parse failure counts.
   - Latency per source.
3. **Dashboards:** A Grafana instance (or a custom view in our Dashboard) visualizing these metrics.
4. **Alerting:** If the success rate for a specific source drops below 80% over a 1-hour window, an alert is triggered (e.g., via Slack or email).
    """,

    "14-testing-strategy.md": """
# Testing Architecture

Testing must assure both application logic and scraper reliability.

## Layers
1. **Unit Tests:** For business logic, index computation, and data normalization.
2. **Parser Tests (Crucial):** We will maintain a repository of saved HTML/JSON fixtures for each source. Parser tests will run against these static files to ensure extraction logic works perfectly and to detect regressions without hitting external networks.
3. **Integration Tests:** Verifying the flow from the Database Repository to the API layer.
4. **End-to-End Tests:** Running a limited scrape job against a mock server to verify the entire pipeline.
5. **Backtesting:** Automated scripts to compare our generated index against historical DGCA public data to validate the methodology.
    """,

    "15-security-ethical-scraping.md": """
# Security and Ethical Scraping

The system must operate professionally and ethically, respecting the resources of the target websites.

## Policies
1. **Robots.txt:** The scraping engine will parse and respect `robots.txt` directives where applicable.
2. **Rate Limiting:** Strict delays between requests to the same domain (e.g., minimum 2-5 seconds).
3. **Concurrency Limits:** Maximum concurrent connections per domain will be strictly capped.
4. **Identification:** We will use a transparent User-Agent string (e.g., `MoSPI-AirfareIndex-Bot/1.0 (+http://mospi.gov.in/bot-policy)`), declaring intent.
5. **No CAPTCHA Bypassing:** We will not use unethical third-party CAPTCHA solving services. If blocked, we rely on IP rotation and backoff.

## Security
API endpoints will require authentication (API keys) for write access or sensitive data access.
    """,

    "16-deployment.md": """
# Deployment

We support two deployment profiles to accommodate the hackathon environment and future production use.

## A. SIH / Hackathon Deployment
A simple Docker Compose setup.
- Container 1: FastAPI (API + Scraper Scheduler)
- Container 2: React Dashboard
- Container 3: PostgreSQL Database
- Container 4: Playwright Browser Instance (if needed for isolated headless browsing)

## B. Production-Scale Architecture
For NSO deployment:
- Kubernetes (EKS/GKE).
- Managed PostgreSQL (RDS/Cloud SQL).
- Dedicated worker nodes for scraper jobs to isolate compute resources from the API.
- S3 for raw data storage.
- CloudWatch/Prometheus for observability.
    """,

    "17-implementation-roadmap.md": """
# Implementation Roadmap

A phased approach for the SIH 2026 hackathon.

- **Stage 0:** Repository foundation (skeleton, linting, CI).
- **Stage 1:** Define Canonical Domain Models (SQLAlchemy + Pydantic).
- **Stage 2:** Implement Scraping Engine Core (Fetchers, Sessions).
- **Stage 3:** First Airline Integration (e.g., IndiGo adapter).
- **Stage 4:** Raw Data Storage and Data Pipeline skeleton.
- **Stage 5:** Normalization & Quality Checks logic.
- **Stage 6:** Job Orchestration (APScheduler setup).
- **Stage 7:** Implement remaining sources (OTAs, other airlines).
- **Stage 8:** Index Engine (aggregation & weighting methodology).
- **Stage 9:** API Development (FastAPI endpoints).
- **Stage 10:** Dashboard Development (UI/UX).
- **Stage 11:** Observability setup.
- **Stage 12:** Backtesting against DGCA data.
- **Stage 13:** Polish & Demo preparation.
    """,

    "18-codebase-file-map.md": """
# Codebase File Map

The repository is structured to separate concerns and allow parallel development.

- `/apps/api/`: FastAPI application, routers, API schemas.
- `/apps/dashboard/`: React/Vue frontend code.
- `/packages/scraping/`: The core scraping engine, fetchers, and source adapters.
- `/packages/domain/`: Shared data models (Pydantic, SQLAlchemy) used across packages.
- `/packages/data_pipeline/`: Logic for validation, cleaning, and normalization.
- `/packages/index_engine/`: Statistical methodology for index computation.
- `/packages/observability/`: Logging setup and metrics collection.
- `/infrastructure/`: Dockerfiles, compose files, k8s manifests, DB migrations.
- `/tests/`: Unit, integration, and fixture-based parser tests.
- `/scripts/`: Utility scripts for DB initialization, manual scrape runs.
- `/docs/`: Architecture and API documentation.
    """,

    "19-scrapling-lessons.md": """
# Lessons from Scrapling

The Scrapling repository provided valuable insights into building a resilient scraping architecture without the overhead of massive frameworks.

## Concepts Adapted
1. **Fetcher Abstraction:** Scrapling's distinct separation between HTTP and Browser fetching is adopted. Our engine dynamically routes requests based on source requirements.
2. **Adaptive Responses:** We utilize dynamic response parsing, where the response object provides helper methods for JSON and HTML extraction, isolating the adapter from underlying HTTP library details.
3. **Session Management:** Centralized management of cookies and headers to mimic real user behavior ethically.

## Intentional Differences
- We do not implement generic "crawling" (following arbitrary links). Airfare scraping is highly targeted (specific APIs or form submissions).
- We avoid aggressive anti-bot evasion techniques found in some generalized scrapers, adhering to ethical constraints necessary for a government-sponsored tool.
    """
}

for doc, content in docs.items():
    with open(os.path.join("docs/architecture", doc), "w") as f:
        f.write(content.strip() + "\\n")

with open("ARCHITECTURE_V4.md", "w") as f:
    f.write("# Architecture Index\\n\\n")
    for doc in docs.keys():
        f.write(f"- [{doc}](docs/architecture/{doc})\\n")

print("Docs generated.")
