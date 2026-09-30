# Data Pipeline ETL

## Phase 1: Extract (Raw Storage)
Raw responses (HTML or JSON) from the scrapers are hashed and dumped into a PostgreSQL JSONB column (`raw_quotes`) or an S3 bucket partitioned by `date/source/`. 
**Why:** If an adapter parser is updated to fix a bug, we can replay the raw data through the pipeline without re-scraping the source.

## Phase 2: Transform & Schema Validation
The parser outputs `RawFareQuote` objects. These are immediately validated using Pydantic schemas. Type coercions (e.g., currency strings like "₹ 5,400" to decimal `5400.00`) happen here.

## Phase 3: Normalization & Deduplication
- **Normalization:** Standardizing carrier codes, mapping fare classes (e.g., 'Saver' -> 'Economy').
- **Deduplication:** Hashing `(source, carrier, flight_number, travel_date, scrape_date)`. If duplicates exist, the latest observation wins, or an alert is thrown for anomalies.

## Phase 4: Quality Checks & Outlier Detection
- Using Median Absolute Deviation (MAD), the pipeline identifies quotes that are wildly out of band for their route and window. 
- Flagged quotes are marked `quality_flag = 'OUTLIER'` and quarantined for manual review, preventing them from corrupting the daily index.

## Phase 5: Load
Validated, cleaned quotes are inserted into the canonical `normalized_quotes` SQL table.
