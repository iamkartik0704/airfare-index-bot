# Index Engine Architecture

## Methodology
The engine implements a fixed-basket Laspeyres price index formula, adjusted for hedonic quality changes.
`APIx(d) = 100 * Sum_r( W_r * (P_r_d / P_r_0) * (Q_0 / Q_d) )`

## Core Responsibilities
1. **Aggregation:** Rolls up `normalized_quotes` into a median price per route per purchase window. The median is chosen to resist outlier shocks (e.g., a single flex-fare seat remaining).
2. **Imputation:** If a route/window is missing data (e.g., scraper blocked, or flights sold out), the engine falls back to historical LOCF (Last Observation Carried Forward) or applies class-mean imputation based on DGCA guidelines.
3. **Weighting:** Applies the annual DGCA passenger-traffic weights (`W_r`).
4. **Sub-Indices:** Generates the daily index, weekly rolling average, and T+1/T+7/T+15 sub-indices.

## Interface boundaries
The `IndexEngine` is a standalone Python package. It takes a `DataFrame` of canonical prices and a `DataFrame` of weights as input. It has zero knowledge of the web scrapers or HTTP. This enables offline backtesting and reproducibility.
