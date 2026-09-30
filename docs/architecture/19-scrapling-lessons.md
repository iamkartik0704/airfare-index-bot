# Lessons from Scrapling

## Why Study Scrapling?
Scrapling is a modern, lightweight Python scraping framework. Instead of the monolithic nature of Scrapy, Scrapling favors modularity and modern asynchronous fetchers.

## Borrowed Concepts (Adapted)
1. **Fetcher Abstraction:** 
   - *Scrapling:* Decouples `fetch()` from parsing.
   - *SAFAR Adaption:* We adopt `BaseFetcher`, allowing us to seamlessly swap between `httpx` and `Playwright` depending on the airline's tech stack, without changing the adapter logic.
2. **Response Objects:**
   - *Scrapling:* Provides a unified `Response` object with built-in CSS/XPath selector methods.
   - *SAFAR Adaption:* We use a similar unified `Response` object so parsers don't care if the data came from HTML or an intercepted XHR JSON payload.
3. **Adaptive Selectors:**
   - *Scrapling:* Selectors that fallback or adapt to minor DOM changes.
   - *SAFAR Adaption:* Implemented for critical DOM nodes, reducing brittleness.

## Intentionally Rejected Concepts
1. **Camouflage/Stealth to Defeat Security:**
   - *Scrapling:* Often used to bypass bot-protection.
   - *SAFAR Action:* Rejected. We operate under MoSPI; we must respect bans, avoid CAPTCHA solving, and rely on ethical rate-limits and imputation instead.
2. **Complex Anti-Fingerprinting:**
   - *SAFAR Action:* Unnecessary. We use descriptive User-Agents, and if a site blocks us, we engage in official dialogue rather than an arms race.
