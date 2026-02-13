import os

BOT_NAME = "cairn_scraper"

SPIDER_MODULES = ["cairn_scraper.spiders"]
NEWSPIDER_MODULE = "cairn_scraper.spiders"

# Respectful scraping
USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
)
ROBOTSTXT_OBEY = False
DOWNLOAD_DELAY = float(os.getenv("SCRAPE_DOWNLOAD_DELAY", 1))
CONCURRENT_REQUESTS = 8
CONCURRENT_REQUESTS_PER_DOMAIN = 2

# Scraping limits (-1 = no limit)
SCRAPE_MAX_PAGES = int(os.getenv("SCRAPE_MAX_PAGES", -1))
SCRAPE_MAX_ITEMS_PER_THEME = int(os.getenv("SCRAPE_MAX_ITEMS_PER_THEME", 200))
SCRAPE_RUN_MODE = os.getenv("SCRAPE_RUN_MODE", "full")
SCRAPE_LATEST_MIN_PAGES = int(os.getenv("SCRAPE_LATEST_MIN_PAGES", 3))
SCRAPE_LATEST_KNOWN_PAGE_STREAK = int(os.getenv("SCRAPE_LATEST_KNOWN_PAGE_STREAK", 2))
SCRAPE_BACKFILL_PAGES_PER_RUN = int(os.getenv("SCRAPE_BACKFILL_PAGES_PER_RUN", 3))
SCRAPE_BACKFILL_MAX_NEW_ITEMS = int(os.getenv("SCRAPE_BACKFILL_MAX_NEW_ITEMS", 50))

# Pipelines
ITEM_PIPELINES = {
    "cairn_scraper.pipelines.MongoPipeline": 1,
    "cairn_scraper.pipelines.ElasticsearchPipeline": 2,
}

# Mongo / ES
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/cairn")
ES_HOST = os.getenv("ES_HOST", "http://localhost:9200")
ES_INDEX = os.getenv("ES_INDEX", "cairn_ouvrages")

# Logging
LOG_LEVEL = "INFO"

REQUEST_FINGERPRINTER_IMPLEMENTATION = "2.7"
TWISTED_REACTOR = "twisted.internet.asyncioreactor.AsyncioSelectorReactor"
FEED_EXPORT_ENCODING = "utf-8"
