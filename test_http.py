import asyncio
from packages.scraping.core.fetchers.http import HttpFetcher
from packages.scraping.core.fetchers.base import Request

async def main():
    fetcher = HttpFetcher()
    req = Request(url="https://httpbin.org/get")
    resp = await fetcher.fetch(req)
    print("Status:", resp.status)
    print("Body:", resp.text[:100])

if __name__ == "__main__":
    asyncio.run(main())
