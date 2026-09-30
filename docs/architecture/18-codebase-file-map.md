# Codebase File Map

```text
airfare-index/
├── apps/
│   ├── api/                 # FastAPI backend
│   │   ├── routers/
│   │   ├── services/
│   │   └── main.py
│   └── dashboard/           # Next.js / Vite frontend
│       ├── src/components/
│       └── src/pages/
├── packages/
│   ├── scraping/            # Core scraper engine
│   │   ├── fetchers/        # HTTP & Browser Fetchers
│   │   └── sources/         # Adapters (indigo, mmt, etc.)
│   ├── data_pipeline/       # ETL, normalization, validation
│   ├── index_engine/        # Laspeyres math, imputation
│   └── domain/              # SQLAlchemy & Pydantic models
├── infrastructure/          # Docker Compose, Terraform
├── tests/
│   ├── fixtures/            # Saved HTML/JSON from sites
│   ├── unit/
│   └── e2e/
└── docs/architecture/       # This documentation
```
