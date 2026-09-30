# V3 Architecture Review

## Overview
The V3 architecture proposed an over-engineered solution, heavily reliant on microservices, event streaming (Kafka), and complex container orchestration that exceeds the requirements of an SIH prototype. This document critically reviews the V3 architecture and proposes concrete changes for V4.

## Detailed Critique
### 1. Kafka & Event Streaming
- **Status:** REMOVE
- **Why:** The scale of scraping for a few dozen routes a few times a day does not justify Kafka. A Postgres-backed job queue (or Redis/Celery) is sufficient and far easier to deploy.
- **Replacement:** We will use a relational database table `scrape_jobs` managed by `APScheduler` or a lightweight `Celery` setup.

### 2. Microservices Sprawl
- **Status:** MODIFY
- **Why:** Deploying 10+ microservices for a prototype is an operational nightmare.
- **Replacement:** A modular monolith. Packages like `scraping`, `data_pipeline`, and `index_engine` will live in the same repository and can be deployed together or scaled independently if needed.

### 3. Scraping Brittleness
- **Status:** MODIFY
- **Why:** V3 lacked a strong abstraction for source websites.
- **Replacement:** Introduce the `SourceAdapter` pattern and a custom Fetcher abstraction (inspired by Scrapling) to isolate HTML/network changes from the core processing logic.

### 4. Raw Data Preservation
- **Status:** ADD
- **Why:** V3 did not explicitly mandate storing raw HTML/JSON responses. We must store raw payloads to allow replayability and parser regression testing.
- **Replacement:** All raw payloads will be stored in S3 or local disk, referenced by `evidence_id` in the database.

### 5. Over-engineered Security
- **Status:** MODIFY
- **Why:** Complex proxy meshes are unnecessary and ethically questionable.
- **Replacement:** Simple session management, exponential backoff, and adherence to `robots.txt`.
