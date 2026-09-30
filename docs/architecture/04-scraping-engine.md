# Scraping Engine Architecture

## Overview
The Scraping Engine is the core data acquisition module. It borrows heavily from the *Scrapling* repository's philosophy: separating network transport, session state, and DOM parsing into clean, interchangeable abstractions.

## Core Abstractions

### `BaseFetcher`
An interface defining `fetch(request: Request) -> Response`. It abstracts away whether a request is made via standard HTTP or a headless browser.

### `HttpFetcher`
Uses `httpx` or `aiohttp` for lightweight, fast HTTP requests. Used for APIs and static HTML sites (e.g., older OTA endpoints or internal flight APIs).
- **Features:** Connection pooling, HTTP/2 support, automatic retry on 5xx errors.

### `BrowserFetcher`
Wraps Playwright for sites that require JavaScript execution (e.g., IndiGo, MakeMyTrip).
- **Optimization:** Intercepts and aborts loading of images, CSS, and third-party trackers to speed up execution and reduce bandwidth.

### `SessionManager`
Maintains cookies, headers, and local storage across multiple requests to a single source, simulating a continuous user session and reducing block rates.

### `ProxyManager`
Rotates through a pool of datacenter or residential proxies (where legally permissible). It detects bans based on HTTP status or specific HTML elements and quarantine proxies.

### `XHR/API Capture`
Instead of parsing complex React DOMs, the `BrowserFetcher` can attach network listeners to capture the underlying JSON API responses sent to the frontend. This is significantly more resilient to UI changes.

## Anti-Bot Compliance
The engine uses:
1. **Exponential Backoff:** Configurable retries for 429 Too Many Requests.
2. **Circuit Breakers:** If a source returns 5 consecutive failures, the source is marked `DEGRADED` and skipped for the rest of the sweep.
3. **Descriptive User-Agents:** Explicitly identifying as the MoSPI/NSO SAFAR bot with a contact URL.
