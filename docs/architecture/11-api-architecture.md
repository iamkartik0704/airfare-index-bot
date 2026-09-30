# API Architecture

## Framework
FastAPI (Python). Selected for async performance, automatic OpenAPI documentation, and strict type checking via Pydantic.

## Key Endpoints

### `/api/v1/index/daily`
- **GET:** Returns the headline APIx for a given date range.
- **Query Params:** `start_date`, `end_date`, `window` (optional filter).

### `/api/v1/routes/{origin}-{destination}/trends`
- **GET:** Returns the lead-time elasticity curve for a specific route.

### `/api/v1/system/health`
- **GET:** Returns the status of the scraping engine, highlighting any blocked or degraded sources.

### `/api/v1/data/quotes`
- **GET:** Protected endpoint for NSO analysts to download the canonical dataset underlying the index for a given day.

## Layered Design
- **Routers:** Handle HTTP requests and routing.
- **Services:** Business logic (e.g., orchestrating DB calls and formatting responses).
- **Repositories:** Abstract the SQLAlchemy DB interactions.
- **Schemas:** Pydantic models for request validation and response serialization.
