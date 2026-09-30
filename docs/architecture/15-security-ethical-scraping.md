# Security and Ethical Scraping Policy

## The MoSPI Mandate
As a government-sponsored initiative, SAFAR cannot engage in malicious bot behaviors. The system must collect public data ethically.

## Core Directives
1. **Robots.txt Awareness:** The `Governance` module must parse and respect `robots.txt` directives and `Crawl-delay`. If a path is disallowed, it must not be scraped.
2. **No CAPTCHA Bypassing:** We do not employ third-party CAPTCHA solving services. If challenged, we back off, flag the source as blocked, and rely on the Index Engine's imputation logic.
3. **Transparent Identification:** All requests must use a descriptive `User-Agent` (e.g., `MoSPI-SAFAR-Bot/1.0 (+https://mospi.gov.in/safar)`).
4. **Rate Limiting:** Global token-bucket rate limiters enforce a maximum requests-per-minute threshold per domain to ensure we do not impact partner infrastructure.
5. **No PII:** The system must never attempt to log in or access user-specific booking flows.

## Credential Management
API keys for legitimate proxies, database passwords, and internal secrets are managed via environment variables (e.g., `dotenv` in dev, AWS Secrets Manager/Hashicorp Vault in prod).
