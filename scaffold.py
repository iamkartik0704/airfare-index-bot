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

docs = [
    "00-executive-summary.md",
    "01-requirements-analysis.md",
    "02-v3-review.md",
    "03-system-architecture.md",
    "04-scraping-engine.md",
    "05-source-adapters.md",
    "06-domain-model.md",
    "07-data-pipeline.md",
    "08-database-design.md",
    "09-index-engine.md",
    "10-job-orchestration.md",
    "11-api-architecture.md",
    "12-dashboard-architecture.md",
    "13-observability.md",
    "14-testing-strategy.md",
    "15-security-ethical-scraping.md",
    "16-deployment.md",
    "17-implementation-roadmap.md",
    "18-codebase-file-map.md",
    "19-scrapling-lessons.md"
]

for doc in docs:
    with open(os.path.join("docs/architecture", doc), "w") as f:
        f.write(f"# {doc.replace('.md', '').replace('-', ' ').title()}\n\nContent to be added based on V4 architecture review.\n")

with open("ARCHITECTURE_V4.md", "w") as f:
    f.write("# Architecture Index\n\n")
    for doc in docs:
        f.write(f"- [{doc}](docs/architecture/{doc})\n")

print("Scaffold complete.")
