import os

folders = [
    "apps/api",
    "apps/dashboard",
    "packages/scraping/sources/airlines/indigo",
    "packages/scraping/sources/airlines/air_india",
    "packages/scraping/sources/otas/makemytrip",
    "packages/domain",
    "packages/data_pipeline",
    "packages/index_engine",
    "packages/observability",
    "infrastructure",
    "tests",
    "scripts",
    "docs/architecture",
    "docs/pdf"
]

for folder in folders:
    os.makedirs(folder, exist_ok=True)
    with open(os.path.join(folder, ".gitkeep"), "w") as f:
        f.write("")

docs = {
    "00-executive-summary.md": "Executive Summary: The architecture focuses on stable, scalable airfare scraping with ethical considerations.",
    "01-requirements-analysis.md": "Requirements: Daily, weekly, monthly airfare index calculation, historical analysis.",
    "02-v3-review.md": "V3 Review: Removed Kafka and unnecessary microservices. Simplified the data pipeline.",
    "03-system-architecture.md": "System Architecture: Modular design with packages for scraping, domain models, pipeline, and API.",
    "04-scraping-engine.md": "Scraping Engine: Employs modular fetchers (HTTP, Browser) with rate limiting and retry logic.",
    "05-source-adapters.md": "Source Adapters: Isolates website-specific extraction logic from canonical processing.",
    "06-domain-model.md": "Domain Model: Canonical representation of AirfareQuote, FlightSegment, Route.",
    "07-data-pipeline.md": "Data Pipeline: Raw response -> extraction -> validation -> normalization -> storage.",
    "08-database-design.md": "Database Design: PostgreSQL schemas for raw_quotes, normalized_quotes, index_values.",
    "09-index-engine.md": "Index Engine: Methodology for weighting and calculating daily/weekly price indices.",
    "10-job-orchestration.md": "Job Orchestration: APScheduler for job scheduling and retry management.",
    "11-api-architecture.md": "API Architecture: FastAPI providing endpoints for historical fares and index data.",
    "12-dashboard-architecture.md": "Dashboard Architecture: UI for visualizing airfare trends and source health.",
    "13-observability.md": "Observability: Metrics and logging for scrape success/failure rates.",
    "14-testing-strategy.md": "Testing Strategy: Unit, integration, and E2E tests using saved HTML fixtures.",
    "15-security-ethical-scraping.md": "Security: Rate limiting, respect for robots.txt, no aggressive CAPTCHA bypassing.",
    "16-deployment.md": "Deployment: Dockerized setup for hackathon, scalable cloud architecture for production.",
    "17-implementation-roadmap.md": "Roadmap: Phased implementation starting with domain models and scraping core.",
    "18-codebase-file-map.md": "File Map: Details the responsibilities of apps/, packages/, tests/.",
    "19-scrapling-lessons.md": "Lessons from Scrapling: Adapted intelligent fetcher selection and session management."
}

for doc, content in docs.items():
    with open(os.path.join("docs/architecture", doc), "w") as f:
        f.write(f"# {doc.replace('.md', '').replace('-', ' ').title()}\n\n{content}\n")

with open("ARCHITECTURE_V4.md", "w") as f:
    f.write("# Architecture Index\n\n")
    for doc in docs.keys():
        f.write(f"- [{doc}](docs/architecture/{doc})\n")

# PDF Generation Tooling
generate_script = """#!/bin/bash
# Install pandoc if not available: sudo apt-get install pandoc texlive-latex-base
echo "Generating SIH26056_Architecture_Plan_V4.pdf"
pandoc docs/architecture/00-executive-summary.md docs/architecture/03-system-architecture.md -o docs/pdf/SIH26056_Architecture_Plan_V4.pdf

echo "Generating SIH26056_Implementation_Blueprint.pdf"
pandoc docs/architecture/08-database-design.md docs/architecture/11-api-architecture.md docs/architecture/17-implementation-roadmap.md docs/architecture/18-codebase-file-map.md -o docs/pdf/SIH26056_Implementation_Blueprint.pdf

echo "Generating SIH26056_Scraping_Architecture.pdf"
pandoc docs/architecture/04-scraping-engine.md docs/architecture/05-source-adapters.md docs/architecture/19-scrapling-lessons.md -o docs/pdf/SIH26056_Scraping_Architecture.pdf

echo "PDF Generation complete."
"""
with open("docs/pdf/generate_pdfs.sh", "w") as f:
    f.write(generate_script)
os.chmod("docs/pdf/generate_pdfs.sh", 0o755)

print("Scaffold V2 complete.")
