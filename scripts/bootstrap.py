"""Entrypoint for the scraper container: wait → init index → crawl."""

import subprocess
import sys

from wait_for_services import wait_mongo, wait_es
from init_es_index import main as init_index


if __name__ == "__main__":
    print("==> Waiting for services...")
    wait_mongo()
    wait_es()

    print("==> Initializing ES index...")
    init_index()

    print("==> Starting scraper...")
    result = subprocess.run(
        [sys.executable, "-m", "scrapy", "crawl", "ouvrages"],
        cwd="scraper",
    )
    sys.exit(result.returncode)
