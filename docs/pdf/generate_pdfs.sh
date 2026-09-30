#!/bin/bash
# Install pandoc if not available: sudo apt-get install pandoc texlive-latex-base
echo "Generating SIH26056_Architecture_Plan_V4.pdf"
pandoc docs/architecture/00-executive-summary.md docs/architecture/03-system-architecture.md -o docs/pdf/SIH26056_Architecture_Plan_V4.pdf

echo "Generating SIH26056_Implementation_Blueprint.pdf"
pandoc docs/architecture/08-database-design.md docs/architecture/11-api-architecture.md docs/architecture/17-implementation-roadmap.md docs/architecture/18-codebase-file-map.md -o docs/pdf/SIH26056_Implementation_Blueprint.pdf

echo "Generating SIH26056_Scraping_Architecture.pdf"
pandoc docs/architecture/04-scraping-engine.md docs/architecture/05-source-adapters.md docs/architecture/19-scrapling-lessons.md -o docs/pdf/SIH26056_Scraping_Architecture.pdf

echo "PDF Generation complete."
