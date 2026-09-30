# Source Adapter Architecture

## The Adapter Pattern
The rest of the SAFAR system must not know about the HTML or JSON structure of individual airlines or OTAs. We achieve this via the `SourceAdapter` interface.

## Directory Structure
```
packages/scraping/sources/
├── base.py               # Defines BaseSourceAdapter
├── airlines/
│   ├── indigo.py         # IndiGo adapter
│   ├── air_india.py      # Air India adapter
│   └── ...
└── otas/
    ├── makemytrip.py     # MMT adapter
    └── ...
```

## `BaseSourceAdapter` Contract
Every adapter must implement:
1. `metadata()`: Returns source capabilities, rate limits, and allowed purchase windows.
2. `build_requests(context: ScrapeContext) -> List[Request]`: Translates a SAFAR route/date context into HTTP/Browser requests.
3. `parse(response: Response) -> List[RawFareQuote]`: Extracts raw quotes from the DOM/JSON.
4. `health_check()`: A fast endpoint check to verify the source is up and the DOM structure hasn't radically changed.

## Defensive Parsing
Adapters use resilient CSS/XPath selectors or rely on XHR capture. If an adapter fails to find a mandatory field (e.g., `base_fare`), it raises a `ParseError`, which flags the scrape job for review rather than silently dropping data or inserting zeros.
