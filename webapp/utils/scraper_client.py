"""Client HTTP simple pour piloter le worker de scraping."""

import json
import os
from urllib import error, request


class ScraperClient:
    def __init__(self, base_url=None):
        self.base_url = (base_url or os.getenv("SCRAPER_API_URL", "http://scraper:8000")).rstrip("/")

    def get_status(self):
        return self._send("GET", "/jobs/status")

    def start_latest(self):
        return self._send("POST", "/jobs/latest")

    def start_backfill(self):
        return self._send("POST", "/jobs/backfill")

    def _send(self, method, path):
        url = f"{self.base_url}{path}"
        req = request.Request(url=url, method=method)
        req.add_header("Content-Type", "application/json")

        try:
            with request.urlopen(req, timeout=5) as response:
                raw = response.read().decode("utf-8")
                payload = json.loads(raw) if raw else {}
                return {
                    "ok": True,
                    "status_code": response.status,
                    "data": payload,
                    "error": "",
                }
        except error.HTTPError as http_error:
            raw_error = http_error.read().decode("utf-8")
            payload = {}
            if raw_error:
                try:
                    payload = json.loads(raw_error)
                except Exception:
                    payload = {"raw_error": raw_error}
            return {
                "ok": False,
                "status_code": http_error.code,
                "data": payload,
                "error": f"HTTP {http_error.code}",
            }
        except Exception as runtime_error:
            return {
                "ok": False,
                "status_code": 0,
                "data": {},
                "error": str(runtime_error),
            }
