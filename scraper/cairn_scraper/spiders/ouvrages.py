import re
from urllib.parse import urlparse, urlencode, urlunparse, parse_qs

import scrapy

from cairn_scraper.items import OuvrageItem


class OuvragesSpider(scrapy.Spider):
    name = "ouvrages"

    THEME_URLS = [
        ("Sciences humaines et sociales", "https://shs.cairn.info/publications?lang=fr&tab=ouvrages"),
        ("Sciences et techniques", "https://stm.cairn.info/publications?lang=fr&tab=ouvrages"),
        ("Droit", "https://droit.cairn.info/publications?lang=fr&tab=ouvrages"),
    ]

    custom_settings = {
        "DEFAULT_REQUEST_HEADERS": {
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "fr-FR,fr;q=0.9,en-US;q=0.8,en;q=0.7",
        },
    }

    @classmethod
    def from_crawler(cls, crawler, *args, **kwargs):
        spider = super().from_crawler(crawler, *args, **kwargs)
        spider.max_pages = crawler.settings.getint("SCRAPE_MAX_PAGES", 0)
        spider.max_per_theme = crawler.settings.getint("SCRAPE_MAX_ITEMS_PER_THEME", 0)
        spider.theme_counts = {}
        return spider

    async def start(self):
        for theme_name, url in self.THEME_URLS:
            self.theme_counts[theme_name] = 0
            yield scrapy.Request(
                url,
                callback=self.parse,
                cb_kwargs={"theme": theme_name, "page": 1},
            )

    def parse(self, response, theme, page):
        links = response.css('a[aria-label^="Consulter l\'ouvrage"]::attr(href)').getall()
        if not links:
            self.logger.warning("No book links found on %s", response.url)
            return

        items_per_page = len(links)

        # only keep links within the per-theme quota
        if self.max_per_theme > 0:
            remaining = self.max_per_theme - self.theme_counts[theme]
            if remaining <= 0:
                return
            links = links[:remaining]

        for href in links:
            yield scrapy.Request(
                response.urljoin(href),
                callback=self.parse_ouvrage,
                cb_kwargs={"theme": theme},
            )

        if page != 1:
            return

        last_page = self._extract_last_page(response) or 1
        end = last_page
        if self.max_pages > 0:
            end = min(end, self.max_pages)
        if self.max_per_theme > 0 and items_per_page > 0:
            end = min(end, -(-self.max_per_theme // items_per_page))

        for p in range(2, end + 1):
            yield scrapy.Request(
                self._build_page_url(response.url, p),
                callback=self.parse,
                cb_kwargs={"theme": theme, "page": p},
            )

    def parse_ouvrage(self, response, theme):
        # skip if we already hit the limit for this theme
        if self.max_per_theme > 0 and self.theme_counts.get(theme, 0) >= self.max_per_theme:
            return

        item = OuvrageItem()

        item["isbn"] = response.css('meta[name="citation_isbn"]::attr(content)').get("")
        item["image_url"] = response.css('meta[property="og:image"]::attr(content)').get("")

        item["title"] = self._clean(response.css("h1::text").get(""))
        item["subtitle"] = self._clean(response.css("h1 + h2::text").get(""))

        item["authors"] = response.css(
            'meta[name="citation_author"]::attr(content)'
        ).getall()

        item["editeur"] = self._clean(
            response.css('meta[name="citation_publisher"]::attr(content)').get("")
        )

        collection_el = response.xpath(
            '//span[contains(@class,"font-serif") and contains(text(),"Collection")]/following-sibling::span/text()'
        )
        item["collection"] = self._clean(collection_el.get(""))

        pages_match = re.search(r"(\d+)\s*pages", response.text)
        item["pages"] = int(pages_match.group(1)) if pages_match else None

        price_text = response.css(
            "p.text-cairn-main.text-center::text"
        ).re_first(r"([\d,]+)\s*€")
        item["price"] = float(price_text.replace(",", ".")) if price_text else None

        body_text = response.text
        date_par = re.search(r"Date de parution\s*:\s*([\d/]+)", body_text)
        item["date_parution"] = date_par.group(1) if date_par else None

        date_mel = re.search(r"Date de mise en ligne\s*:\s*([\d/]+)", body_text)
        item["date_mise_en_ligne"] = date_mel.group(1) if date_mel else None

        desc_div = response.xpath(
            '//h2[contains(text(),"Présentation")]/following-sibling::div[1]'
        )
        item["description"] = self._clean(
            " ".join(desc_div.css("::text").getall())
        )

        item["theme"] = theme
        item["url"] = response.url

        item["doc_id"] = urlparse(response.url).path.strip("/")

        self.theme_counts[theme] += 1
        yield item

    @staticmethod
    def _extract_last_page(response):
        pages = response.css(
            'nav[aria-label="Pagination"] button[aria-label*="page"]::attr(aria-label)'
        ).re(r"(\d+)")
        if pages:
            return max(int(p) for p in pages)
        return None

    @staticmethod
    def _build_page_url(base_url, page):
        parsed = urlparse(base_url)
        params = parse_qs(parsed.query)
        params["page"] = [str(page)]
        new_query = urlencode(params, doseq=True)
        return urlunparse(parsed._replace(query=new_query))

    @staticmethod
    def _clean(text):
        if not text:
            return ""
        return re.sub(r"\s+", " ", text).strip()
