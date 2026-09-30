# Observability Strategy

## The Need
A scraper failing silently is the biggest risk to the CPI. We must know immediately if a parser breaks due to a UI update.

## Metrics
Tracked via Prometheus/Grafana or a managed service (Datadog/NewRelic):
- `scrape_success_rate` (Gauge, by Source)
- `http_status_codes` (Counter, by Source)
- `parser_failure_rate` (Counter)
- `data_freshness_seconds` (Gauge)
- `missing_fare_count` (Counter)

## Logging
Structured JSON logging using Python's `structlog`.
Fields required on every log: `timestamp`, `level`, `job_id`, `source`, `event`.

## Alerts
- **Critical:** Headline Index computation failed or zero quotes scraped for >24 hours.
- **High:** A major source (e.g., IndiGo, MMT) has a 100% failure rate for >2 hours.
- **Warning:** Parser encountering unusual amounts of "missing" convenience fees.
