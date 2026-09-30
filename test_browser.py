import asyncio
from packages.scraping.core.fetchers.browser import BrowserFetcher
from packages.scraping.core.fetchers.base import Request

async def main():
    fetcher = BrowserFetcher()
    req = Request(url="https://example.com")
    resp = await fetcher.fetch(req)
    print("Status:", resp.status)
    print("Type:", type(resp.body))
    print("Body starts with:", resp.body[:100] if isinstance(resp.body, bytes) else resp.body)
    await fetcher.close()

asyncio.run(main())
