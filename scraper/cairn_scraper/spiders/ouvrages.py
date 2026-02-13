import json
import re
from datetime import datetime, timezone
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

import scrapy
from pymongo import MongoClient

from cairn_scraper.items import OuvrageItem


class OuvragesSpider(scrapy.Spider):
    name = "ouvrages"

    THEME_URLS = [
        ("Sciences humaines et sociales", "https://shs.cairn.info/publications?lang=fr&tab=ouvrages"),
        ("Sciences et techniques", "https://stm.cairn.info/publications?lang=fr&tab=ouvrages"),
        ("Droit", "https://droit.cairn.info/publications?lang=fr&tab=ouvrages"),
    ]

    DEFAULT_LATEST_MIN_PAGES = 3
    DEFAULT_LATEST_KNOWN_PAGE_STREAK = 2
    DEFAULT_BACKFILL_PAGES_PER_RUN = 3
    DEFAULT_BACKFILL_MAX_NEW_ITEMS = 50

    custom_settings = {
        "DEFAULT_REQUEST_HEADERS": {
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "fr-FR,fr;q=0.9,en-US;q=0.8,en;q=0.7",
        },
    }

    @classmethod
    def from_crawler(cls, crawler, *args, **kwargs):
        spider = super().from_crawler(crawler, *args, **kwargs)
        spider.max_pages = crawler.settings.getint("SCRAPE_MAX_PAGES", -1)
        spider.max_per_theme = crawler.settings.getint("SCRAPE_MAX_ITEMS_PER_THEME", -1)
        spider.latest_min_pages = crawler.settings.getint(
            "SCRAPE_LATEST_MIN_PAGES",
            cls.DEFAULT_LATEST_MIN_PAGES,
        )
        spider.latest_known_page_streak = crawler.settings.getint(
            "SCRAPE_LATEST_KNOWN_PAGE_STREAK",
            cls.DEFAULT_LATEST_KNOWN_PAGE_STREAK,
        )
        spider.backfill_pages_per_run = crawler.settings.getint(
            "SCRAPE_BACKFILL_PAGES_PER_RUN",
            cls.DEFAULT_BACKFILL_PAGES_PER_RUN,
        )
        spider.backfill_max_new_items = crawler.settings.getint(
            "SCRAPE_BACKFILL_MAX_NEW_ITEMS",
            cls.DEFAULT_BACKFILL_MAX_NEW_ITEMS,
        )

        run_mode = kwargs.get("run_mode") or crawler.settings.get("SCRAPE_RUN_MODE", "full")
        spider.run_mode = str(run_mode).strip().lower()
        if spider.run_mode not in {"full", "latest", "backfill"}:
            spider.logger.warning("Unknown run_mode='%s'. Falling back to 'full'.", spider.run_mode)
            spider.run_mode = "full"

        spider.stats_path = kwargs.get("stats_path", "")
        spider.run_started_at = datetime.now(timezone.utc).isoformat()

        spider.theme_base_urls = {}
        spider.theme_counts = {}
        spider.theme_pending_counts = {}
        spider.theme_page_progress = {}
        spider.backfill_target_end_page = {}
        spider.scheduled_new_items = 0

        spider.mongo_uri = crawler.settings.get("MONGO_URI")
        spider.mongo_client = None
        spider.mongo_db = None
        spider.mongo_ouvrages = None
        spider.mongo_state = None
        spider._open_mongo()
        return spider

    async def start(self):
        for theme_name, url in self.THEME_URLS:
            self.theme_base_urls[theme_name] = url
            self.theme_counts[theme_name] = 0
            self.theme_pending_counts[theme_name] = 0

            start_page = 1
            if self.run_mode == "backfill":
                start_page = self._get_backfill_start_page(theme_name)
                pages_to_scan = max(self.backfill_pages_per_run, 1)
                self.backfill_target_end_page[theme_name] = start_page + pages_to_scan - 1

            self.theme_page_progress[theme_name] = {
                "start_page": start_page,
                "last_page_scanned": 0,
                "pages_scanned": 0,
                "known_page_streak": 0,
                "new_links_found": 0,
                "stopped_reason": "",
            }

            first_url = url if start_page == 1 else self._build_page_url(url, start_page)
            yield scrapy.Request(
                first_url,
                callback=self.parse,
                cb_kwargs={"theme": theme_name, "page": start_page},
            )

    def parse(self, response, theme, page):
        if self.run_mode == "full":
            yield from self._parse_full(response, theme, page)
            return

        yield from self._parse_incremental(response, theme, page)

    def _parse_full(self, response, theme, page):
        entries = self._extract_listing_entries(response)
        if not entries:
            self.logger.warning("No book links found on %s", response.url)
            return

        items_per_page = len(entries)
        self._mark_page_scanned(theme, page)

        if self.max_per_theme >= 0:
            remaining = self.max_per_theme - self.theme_counts[theme]
            if remaining <= 0:
                self.theme_page_progress[theme]["stopped_reason"] = "max_per_theme reached"
                return
            entries = entries[:remaining]

        for entry in entries:
            yield scrapy.Request(
                entry["url"],
                callback=self.parse_ouvrage,
                cb_kwargs={"theme": theme},
            )

        if page != 1:
            return

        last_page = self._extract_last_page(response) or 1
        end_page = last_page

        if self.max_pages >= 0:
            end_page = min(end_page, self.max_pages)

        if self.max_per_theme >= 0 and items_per_page > 0:
            page_limit_for_items = -(-self.max_per_theme // items_per_page)
            end_page = min(end_page, page_limit_for_items)

        for next_page in range(2, end_page + 1):
            yield scrapy.Request(
                self._build_page_url(self.theme_base_urls[theme], next_page),
                callback=self.parse,
                cb_kwargs={"theme": theme, "page": next_page},
            )

    def _parse_incremental(self, response, theme, page):
        entries = self._extract_listing_entries(response)
        if not entries:
            self.logger.warning("No book links found on %s", response.url)
            self._mark_page_scanned(theme, page)
            self.theme_page_progress[theme]["stopped_reason"] = "no listing entries found"
            self._persist_theme_state(theme)
            return

        doc_ids = []
        for entry in entries:
            doc_ids.append(entry["doc_id"])
        known_doc_ids = self._load_known_doc_ids(doc_ids)

        unknown_entries = []
        for entry in entries:
            is_known = entry["doc_id"] in known_doc_ids
            if not is_known:
                unknown_entries.append(entry)

        if self.max_per_theme >= 0:
            remaining = self.max_per_theme - (
                self.theme_counts[theme] + self.theme_pending_counts[theme]
            )
            if remaining <= 0:
                self.theme_page_progress[theme]["stopped_reason"] = "max_per_theme reached"
                self._persist_theme_state(theme)
                return
            unknown_entries = unknown_entries[:remaining]

        if self.run_mode == "backfill":
            remaining_backfill_slots = self._remaining_backfill_slots()
            if remaining_backfill_slots == 0:
                self.theme_page_progress[theme]["stopped_reason"] = "backfill max new items reached"
                self._persist_theme_state(theme)
                return
            if remaining_backfill_slots > 0:
                unknown_entries = unknown_entries[:remaining_backfill_slots]

        for entry in unknown_entries:
            self.scheduled_new_items += 1
            self.theme_pending_counts[theme] += 1
            yield scrapy.Request(
                entry["url"],
                callback=self.parse_ouvrage,
                errback=self.parse_ouvrage_error,
                cb_kwargs={"theme": theme},
            )

        self._mark_page_scanned(theme, page)
        self.theme_page_progress[theme]["new_links_found"] += len(unknown_entries)

        page_is_fully_known = len(entries) > 0 and len(unknown_entries) == 0
        if page_is_fully_known:
            self.theme_page_progress[theme]["known_page_streak"] += 1
        else:
            self.theme_page_progress[theme]["known_page_streak"] = 0

        last_page_on_site = self._extract_last_page(response)
        stop_reason = self._get_stop_reason(theme, page, last_page_on_site)
        if stop_reason:
            self.theme_page_progress[theme]["stopped_reason"] = stop_reason
            self._persist_theme_state(theme)
            return

        next_page = page + 1
        yield scrapy.Request(
            self._build_page_url(self.theme_base_urls[theme], next_page),
            callback=self.parse,
            cb_kwargs={"theme": theme, "page": next_page},
        )

    def parse_ouvrage(self, response, theme):
        self._consume_pending_slot(theme)
        if self.max_per_theme >= 0 and self.theme_counts.get(theme, 0) >= self.max_per_theme:
            return

        item = OuvrageItem()
        item["isbn"] = response.css('meta[name="citation_isbn"]::attr(content)').get("")
        item["image_url"] = response.css('meta[property="og:image"]::attr(content)').get("")
        item["title"] = self._clean(response.css("h1::text").get(""))
        item["subtitle"] = self._clean(response.css("h1 + h2::text").get(""))
        item["authors"] = response.css('meta[name="citation_author"]::attr(content)').getall()
        item["editeur"] = self._clean(
            response.css('meta[name="citation_publisher"]::attr(content)').get("")
        )

        collection_el = response.xpath(
            '//span[contains(@class,"font-serif") and contains(text(),"Collection")]/following-sibling::span/text()'
        )
        item["collection"] = self._clean(collection_el.get(""))

        pages_match = re.search(r"(\d+)\s*pages", response.text)
        item["pages"] = int(pages_match.group(1)) if pages_match else None

        price_text = response.css("p.text-cairn-main.text-center::text").re_first(r"([\d,]+)\s*€")
        item["price"] = float(price_text.replace(",", ".")) if price_text else None

        body_text = response.text
        date_parution_match = re.search(r"Date de parution\s*:\s*([\d/]+)", body_text)
        item["date_parution"] = date_parution_match.group(1) if date_parution_match else None

        date_mise_en_ligne_match = re.search(r"Date de mise en ligne\s*:\s*([\d/]+)", body_text)
        item["date_mise_en_ligne"] = (
            date_mise_en_ligne_match.group(1) if date_mise_en_ligne_match else None
        )

        desc_div = response.xpath('//h2[contains(text(),"Présentation")]/following-sibling::div[1]')
        item["description"] = self._clean(" ".join(desc_div.css("::text").getall()))

        item["theme"] = theme
        item["url"] = response.url
        item["doc_id"] = self._doc_id_from_url(response.url)

        self.theme_counts[theme] += 1
        yield item

    def parse_ouvrage_error(self, failure):
        theme = failure.request.cb_kwargs.get("theme", "")
        self._consume_pending_slot(theme)

    def _consume_pending_slot(self, theme):
        if theme in self.theme_pending_counts and self.theme_pending_counts[theme] > 0:
            self.theme_pending_counts[theme] -= 1

    def closed(self, reason):
        summary = self._build_run_summary(reason)

        if self.stats_path:
            try:
                with open(self.stats_path, "w", encoding="utf-8") as file_handle:
                    json.dump(summary, file_handle, ensure_ascii=True, indent=2)
            except Exception as error:
                self.logger.warning("Could not write stats file '%s': %s", self.stats_path, error)

        if self.mongo_client is not None:
            self.mongo_client.close()

    def _open_mongo(self):
        if not self.mongo_uri:
            self.logger.warning("MONGO_URI missing. Incremental mode will treat all entries as unknown.")
            return

        try:
            parsed = urlparse(self.mongo_uri)
            db_name = parsed.path.lstrip("/") or "cairn"
            self.mongo_client = MongoClient(self.mongo_uri)
            self.mongo_db = self.mongo_client[db_name]
            self.mongo_ouvrages = self.mongo_db["ouvrages"]
            self.mongo_state = self.mongo_db["scrape_state"]
        except Exception as error:
            self.logger.warning("Could not connect to MongoDB: %s", error)
            self.mongo_client = None
            self.mongo_db = None
            self.mongo_ouvrages = None
            self.mongo_state = None

    def _extract_listing_entries(self, response):
        hrefs = response.css('a[aria-label^="Consulter l\'ouvrage"]::attr(href)').getall()
        entries = []

        for href in hrefs:
            absolute_url = response.urljoin(href)
            doc_id = self._doc_id_from_url(absolute_url)
            if not doc_id:
                continue
            entries.append({"url": absolute_url, "doc_id": doc_id})

        return entries

    def _load_known_doc_ids(self, doc_ids):
        known_doc_ids = set()
        if self.mongo_ouvrages is None or not doc_ids:
            return known_doc_ids

        query = {"doc_id": {"$in": doc_ids}}
        projection = {"_id": 0, "doc_id": 1}

        for row in self.mongo_ouvrages.find(query, projection):
            doc_id = row.get("doc_id")
            if doc_id:
                known_doc_ids.add(doc_id)

        return known_doc_ids

    def _mark_page_scanned(self, theme, page):
        progress = self.theme_page_progress[theme]
        progress["pages_scanned"] += 1
        progress["last_page_scanned"] = page

    def _get_stop_reason(self, theme, page, last_page_on_site):
        progress = self.theme_page_progress[theme]

        if self.max_pages >= 0 and progress["pages_scanned"] >= self.max_pages:
            return "SCRAPE_MAX_PAGES reached"

        if self.max_per_theme >= 0:
            total_scheduled_or_scraped = self.theme_counts[theme] + self.theme_pending_counts[theme]
            if total_scheduled_or_scraped >= self.max_per_theme:
                return "max_per_theme reached"

        if last_page_on_site is not None and page >= last_page_on_site:
            return "reached last page on site"

        if self.run_mode == "latest":
            enough_pages_scanned = progress["pages_scanned"] >= max(self.latest_min_pages, 1)
            known_streak_reached = (
                progress["known_page_streak"] >= max(self.latest_known_page_streak, 1)
            )
            if enough_pages_scanned and known_streak_reached:
                return "known page streak reached"

        if self.run_mode == "backfill":
            if self._remaining_backfill_slots() == 0:
                return "backfill max new items reached"

            target_end_page = self.backfill_target_end_page.get(theme, page)
            if page >= target_end_page:
                return "configured backfill depth reached"

        return ""

    def _get_backfill_start_page(self, theme):
        if self.mongo_state is None:
            return 1

        state_doc = self.mongo_state.find_one({"_id": theme})
        if state_doc is None:
            return 1

        value = state_doc.get("next_backfill_page")
        if isinstance(value, int) and value >= 1:
            return value
        return 1

    def _persist_theme_state(self, theme):
        if self.mongo_state is None or self.run_mode not in {"latest", "backfill"}:
            return

        progress = self.theme_page_progress[theme]
        last_page_scanned = progress["last_page_scanned"]
        now = datetime.now(timezone.utc)

        state_doc = self.mongo_state.find_one({"_id": theme}) or {}
        current_next_backfill = state_doc.get("next_backfill_page")
        update_values = {
            "theme": theme,
            "updated_at": now,
        }

        if self.run_mode == "latest":
            update_values["last_latest_scanned_page"] = last_page_scanned
            update_values["last_latest_stopped_reason"] = progress["stopped_reason"]
            update_values["last_latest_new_links"] = progress["new_links_found"]

            next_backfill_page = current_next_backfill
            if not isinstance(next_backfill_page, int) or next_backfill_page <= last_page_scanned:
                next_backfill_page = last_page_scanned + 1
            update_values["next_backfill_page"] = max(next_backfill_page, 1)

        if self.run_mode == "backfill":
            next_backfill_page = max(last_page_scanned + 1, 1)
            update_values["next_backfill_page"] = next_backfill_page
            update_values["last_backfill_scanned_page"] = last_page_scanned
            update_values["last_backfill_stopped_reason"] = progress["stopped_reason"]
            update_values["last_backfill_new_links"] = progress["new_links_found"]

        self.mongo_state.update_one(
            {"_id": theme},
            {"$set": update_values},
            upsert=True,
        )

    def _build_run_summary(self, reason):
        themes = {}
        for theme_name, progress in self.theme_page_progress.items():
            themes[theme_name] = {
                "start_page": progress["start_page"],
                "last_page_scanned": progress["last_page_scanned"],
                "pages_scanned": progress["pages_scanned"],
                "known_page_streak": progress["known_page_streak"],
                "new_links_found": progress["new_links_found"],
                "new_items_scraped": self.theme_counts.get(theme_name, 0),
                "stopped_reason": progress["stopped_reason"],
            }

        return {
            "run_mode": self.run_mode,
            "reason": reason,
            "started_at": self.run_started_at,
            "finished_at": datetime.now(timezone.utc).isoformat(),
            "backfill_max_new_items": self.backfill_max_new_items,
            "scheduled_new_items": self.scheduled_new_items,
            "total_new_items_scraped": sum(self.theme_counts.values()),
            "themes": themes,
        }

    def _remaining_backfill_slots(self):
        if self.backfill_max_new_items < 0:
            return -1

        remaining = self.backfill_max_new_items - self.scheduled_new_items
        if remaining <= 0:
            return 0
        return remaining

    @staticmethod
    def _extract_last_page(response):
        pages = response.css(
            'nav[aria-label="Pagination"] button[aria-label*="page"]::attr(aria-label)'
        ).re(r"(\d+)")
        if pages:
            return max(int(value) for value in pages)
        return None

    @staticmethod
    def _build_page_url(base_url, page):
        parsed = urlparse(base_url)
        params = parse_qs(parsed.query)
        params["page"] = [str(page)]
        new_query = urlencode(params, doseq=True)
        return urlunparse(parsed._replace(query=new_query))

    @staticmethod
    def _doc_id_from_url(url):
        parsed = urlparse(url)
        return parsed.path.strip("/")

    @staticmethod
    def _clean(text):
        if not text:
            return ""
        return re.sub(r"\s+", " ", text).strip()
