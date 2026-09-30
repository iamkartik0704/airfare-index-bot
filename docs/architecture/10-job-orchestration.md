# Job Orchestration

## Scope
Scraping millions of data points requires orchestrating jobs across multiple dimensions: Routes (24) × Sources (11) × Purchase Windows (5) × Dates.

## Architecture
For the SIH Prototype, we utilize **Celery with Redis** as the broker. (APScheduler handles cron-like triggering; Celery handles fan-out and retries). Kafka was rejected as overengineering.

## Job Lifecycle
1. **Trigger:** `01:00 IST` Cron triggers the `SweepGenerator`.
2. **Fan-out:** Generates independent `ScrapeTask`s for each Source-Route-Window combination.
3. **Execution:** Celery workers pick up tasks. The `SourceAdapter` is invoked.
4. **Failure Handling:**
   - Network Timeout? Retry with exponential backoff (up to 3 times).
   - Source HTTP 429 (Rate Limit)? Pause worker queue for that domain, retry later.
   - Parser Error? Send to Dead Letter Queue (DLQ), alert developer.
5. **Completion:** Mark `ScrapeJob` as SUCCESS in DB, trigger the `DataPipeline` ETL task.

## Concurrency Control
Concurrency is limited per domain. We enforce a maximum of 1-3 concurrent workers per OTA/Airline to strictly obey rate limits and `robots.txt` `Crawl-delay`.
