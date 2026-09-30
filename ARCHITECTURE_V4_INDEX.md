# SAFAR Architecture Directory

Welcome to the definitive V4 architectural blueprint for the SAFAR (Statutory Air Fare Analytics & Reporting) system.

## Documentation Index
- [00. Executive Summary](./00-executive-summary.md)
- [01. Requirements Analysis](./01-requirements-analysis.md)
- [02. V3 Review](./02-v3-review.md)
- [03. System Architecture](./03-system-architecture.md)
- [04. Scraping Engine](./04-scraping-engine.md)
- [05. Source Adapters](./05-source-adapters.md)
- [06. Domain Model](./06-domain-model.md)
- [07. Data Pipeline](./07-data-pipeline.md)
- [08. Database Design](./08-database-design.md)
- [09. Index Engine](./09-index-engine.md)
- [10. Job Orchestration](./10-job-orchestration.md)
- [11. API Architecture](./11-api-architecture.md)
- [12. Dashboard Architecture](./12-dashboard-architecture.md)
- [13. Observability](./13-observability.md)
- [14. Testing Strategy](./14-testing-strategy.md)
- [15. Security & Ethical Scraping](./15-security-ethical-scraping.md)
- [16. Deployment](./16-deployment.md)
- [17. Implementation Roadmap](./17-implementation-roadmap.md)
- [18. Codebase File Map](./18-codebase-file-map.md)
- [19. Scrapling Lessons](./19-scrapling-lessons.md)

## Current Status
This architecture replaces V3. It decouples the scraping engine from the data pipeline, introduces an immutable raw data store, and adopts modular fetcher abstractions inspired by Scrapling.
