# Dashboard Architecture

## Tech Stack
React (Next.js/Vite) + Tailwind CSS + Recharts.

## Core Views
1. **The Headline Index:** A large, highly visible chart plotting the Daily APIx over time against the DGCA benchmark.
2. **Sector Heatmap:** A visual matrix showing price intensity across the 24 city-pairs.
3. **Lead-Time Elasticity:** A curve plotting T+1 vs T+7 vs T+45 prices to demonstrate dynamic pricing.
4. **System Console:** Real-time visibility into the scraping workers, showing success rates, active blockages, and data freshness.

## Data Fetching
Uses React Query (or RTK Query) to poll the FastAPI endpoints. The dashboard is entirely decoupled from the backend and holds no domain logic.
