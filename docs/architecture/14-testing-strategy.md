# Testing Architecture

## Offline Parser Validation (Critical)
We capture and store HTML/JSON payloads from real websites as `fixtures/`.
Unit tests assert that `Parser.parse(fixture)` returns the exact expected `NormalizedQuote`.
**Benefit:** We can run the test suite in CI without hitting production websites or worrying about dynamic price changes.

## Layers of Testing
1. **Unit Tests:** Business logic in parsers, normalization rules, and index math.
2. **Contract Tests:** Verifying the DB schemas and API outputs.
3. **Integration Tests:** Verifying the flow from `Adapter` -> `RawStore` -> `NormalizedDB`.
4. **Backtesting (End-to-End Validation):** Running the `IndexEngine` over 30 days of historical data and asserting high correlation (Pearson r > 0.95) with the public DGCA monthly average-fare data.

## Regression Detection
A scheduled CI job runs nightly, fetching 5 live URLs per source and parsing them. If the parser raises an exception, the team is alerted that a website UI update has broken the adapter, before the main sweep is impacted.
