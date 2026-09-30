"""
Scrapy project settings for the production collector.

The reference adapters in `collect/` drive Playwright directly; this module is
the Scrapy path used for the statically-rendered parts of the sources and for
the polite crawl scheduling (AutoThrottle + per-domain delay + robots).

    scrapy crawl safar_fares -a day=2026-09-30
"""

BOTS = {
    "SAFAR": [
        "safar.collect.*",
    ],
}

SPIDER_MODULES = ["safar.spiders"]
NEWSPIDER_MODULE = "safar.spiders"

ROBOTSTXT_OBEY = True          # non-negotiable
ROBOTSTXT_PARSER = "scrapy.robotstxt.PythonRobotParser"
USER_AGENT = (
    "SAFAR-Indexer/1.0 (+https://safar.stats.gov.in/bot; contact: data@safar.stats.gov.in)"
)

CONCURRENT_REQUESTS = 1          # one request at a time per host
CONCURRENT_REQUESTS_PER_DOMAIN = 1
DOWNLOAD_DELAY = 12              # seconds, on top of Crawl-delay from robots.txt
RANDOMIZE_DOWNLOAD_DELAY = True

AUTOTHROTTLE_ENABLED = True
AUTOTHROTTLE_START_DELAY = 8.0
AUTOTHROTTLE_MAX_DELAY = 60.0
AUTOTHROTTLE_TARGET_CONCURRENCY = 1.0

COOKIES_ENABLED = False          # no session reuse across users, no login state
RETRY_ENABLED = True
RETRY_TIMES = 3
RETRY_HTTP_CODES = [500, 502, 503, 504]
DOWNLOAD_TIMEOUT = 45

ITEM_PIPELINES = {
    "safar.pipelines.ValidationPipeline": 100,
    "safar.pipelines.DedupPipeline": 200,
    "safar.pipelines.OutlierPipeline": 300,
}
FEED_EXPORT_ENCODING = "utf-8"
FEEDS = {
    "s3://safar-raw/quotes/%(year)s/%(month)s/%(day)s/%(hour)s.jsonl": {"format": "jsonlines"},
}
LOG_LEVEL = "INFO"

# The pipeline never sees a checkout, login or payment path — enforced in the
# spider's allowed_domains + start_urls and re-checked by robots middleware.
ALLOWED_PATHS = ["/flight", "/booking", "/search", "/domestic-flights"]
