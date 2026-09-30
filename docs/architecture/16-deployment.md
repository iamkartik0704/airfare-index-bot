# Deployment Architecture

## Target A: SIH Hackathon Prototype
A streamlined, reliable setup optimized for the demo.
- **Compute:** Single VPS or Docker Compose instance.
- **Database:** PostgreSQL (running locally in Docker).
- **Orchestration:** Python `APScheduler` or background `Asyncio` tasks instead of Celery/Redis.
- **Frontend/Backend:** Next.js + FastAPI served on the same machine.

## Target B: Production-Scale Architecture (MoSPI)
- **Compute:** Kubernetes (EKS/GKE) with auto-scaling worker nodes.
- **Scraping Cluster:** Playwright workers distributed across pods.
- **Database:** Amazon RDS (PostgreSQL) for relational data, Amazon S3 for the immutable raw JSON store.
- **Message Broker:** Redis or RabbitMQ for Celery job distribution.
- **Observability:** Datadog or Prometheus/Grafana stack.
