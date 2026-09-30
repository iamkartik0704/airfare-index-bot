# Canonical Domain Model

## Core Entities

### `AirfareQuote` (Normalized Output)
The canonical representation of a price observation.
- `id` (UUID)
- `source_id` (String): e.g., 'indigo', 'mmt'
- `scrape_job_id` (UUID): Links back to the orchestrator execution.
- `carrier` (String): Airline code (e.g., '6E', 'AI')
- `flight_number` (String)
- `origin` & `destination` (String): IATA codes (e.g., 'DEL', 'BOM')
- `travel_date` (Date)
- `advance_purchase_days` (Int): Calculated window (T+1, T+7, etc.)
- `base_fare` (Decimal)
- `taxes` (Decimal)
- `convenience_fee` (Decimal)
- `total_fare` (Decimal)
- `availability_status` (Enum): `AVAILABLE`, `SOLD_OUT`, `CANCELLED`

### `ScrapeJob`
Tracks the execution of a sweep.
- `status`: `PENDING`, `RUNNING`, `SUCCESS`, `FAILED`
- `started_at`, `completed_at`
- `items_scraped`, `errors_encountered`

### `IndexObservation`
The computed daily price point for a specific route and window, derived from aggregating `AirfareQuote`s.

## Why these fields?
- **Separation of Fares:** The index must isolate base fare from dynamic convenience fees and taxes, which behave differently.
- **Availability Status:** A sold-out flight represents zero availability, not zero cost. The index engine must know to exclude or impute this, rather than treating it as a missing data point.
- **Job IDs:** Ensures auditability. We can trace any anomaly in the final CPI statistic back to the exact HTML response that generated it.
