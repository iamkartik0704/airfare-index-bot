# Database Architecture

## Relational Engine: PostgreSQL
PostgreSQL is chosen for its JSONB support (essential for the raw store) and robust relational guarantees for the canonical data.

## Key Tables

### `sources`
- `id` (PK), `name`, `type` (AIRLINE/OTA), `status`, `rate_limit_rpm`

### `routes`
- `id` (PK), `origin_iata`, `destination_iata`, `dgca_weight` (Decimal)

### `scrape_jobs`
- `id` (PK), `started_at`, `completed_at`, `status`, `target_date`, `purchase_window`

### `raw_quotes`
- `id` (PK), `job_id` (FK), `source_id` (FK), `raw_payload` (JSONB), `created_at`
- **Purpose:** Immutable audit log. Indexed on `job_id` and `created_at`.

### `normalized_quotes`
- `id` (PK), `raw_id` (FK), `route_id` (FK), `travel_date`, `advance_window`, `carrier`, `base_fare`, `total_fare`
- **Constraints:** Unique on `(route_id, travel_date, carrier, flight_number, scrape_timestamp)`.

### `index_observations`
- `date` (PK), `route_id` (PK), `window` (PK), `median_price`, `imputed` (Boolean)

## Storage Strategy
- Highly structured data (`normalized_quotes`, `index_observations`) uses strict types and constraints.
- Ephemeral or source-specific data (HTML/JSON responses) uses `JSONB` to handle schema drift flexibly.
