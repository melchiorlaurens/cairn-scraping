# cairn-scraping

E4 Data Engineering projet — Scraping [cairn.info](https://cairn.info) — Melchior Laurens & Kévin Feltrin

Scrapy spider that collects academic books from Cairn.info, stores them in **MongoDB** and **Elasticsearch**, and exposes them through a **Streamlit** webapp with search, detail views, statistics dashboards, and a built-in **Scraping helper** page to launch background crawl jobs.

## Architecture

The project follows a classic **ETL** pipeline with a search & visualization layer:

**Cairn.info** → **Scrapy spider** → **MongoDB** + **Elasticsearch** → **Streamlit webapp**

The `OuvragesSpider` scrapes book metadata (title, authors, ISBN, description, price, publisher, collection, dates, page count) across 3 Cairn themes: *Sciences humaines et sociales*, *Sciences et techniques*, and *Droit*. Each scraped item is then passed through two pipelines in parallel: **MongoDB** for persistent raw storage, and **Elasticsearch** (with a French text analyzer) for full-text search, faceted filtering, and aggregations. The **Streamlit webapp** queries Elasticsearch to provide search, detail views, and statistics dashboards powered by Plotly.

### Technology choices

We chose **Scrapy** for scraping because it handles pagination, rate limiting, and storage pipelines out of the box. Scraped data lands in **MongoDB**, which is schema-free — convenient when fields vary from one book to another. For search we went with **Elasticsearch**: it ships with a French text analyzer and supports the aggregations that power the stats dashboards. The frontend is built with **Streamlit**, which lets us go from a Python script to a working web app without writing any frontend code.

### Data Flow

1. **Scraping Phase** (`scraper/`)
   - `OuvragesSpider` crawls pagination across 3 Cairn themes
   - Extracts book metadata using CSS selectors & regex
   - Yields `OuvrageItem` for each book found
   - Configurable limits: `SCRAPE_MAX_PAGES`, `SCRAPE_MAX_ITEMS_PER_THEME`

2. **Storage Phase** (`pipelines.py`)
   - `MongoPipeline`: upserts to MongoDB (by `doc_id`), preserves raw data
   - `ElasticsearchPipeline`: indexes to ES (by `doc_id`), enables search
   - Both pipelines run sequentially on each scraped item

3. **Search & Display Phase** (`webapp/`)
   - `ESClient` wraps Elasticsearch queries (search, aggregations, get by ID)
   - Streamlit pages render results with interactive filters and pagination
   - Charts built with Plotly (distributions, trends, top authors/publishers)

4. **Background Scraping API** (`scripts/scraper_worker.py`)
   - Lightweight HTTP worker in the `scraper` container
   - Endpoints to launch jobs: `latest` and `backfill`
   - Streamlit page calls this API and shows job status

### Key Components

| Component | Technology | Purpose |
|-----------|------------|---------|
| **Spider** | Scrapy | Crawls cairn.info, extracts book metadata |
| **Pipelines** | pymongo + elasticsearch-py | Dual storage: MongoDB (backup) + ES (search) |
| **Index mapping** | Elasticsearch | French analyzer for titles/descriptions, keyword fields for filters |
| **Web app** | Streamlit | Search UI + stats dashboard + scraping helper controls |
| **Scraper worker API** | Python stdlib HTTP server | Launches background scrape jobs + exposes status |
| **Search client** | `ESClient` | Wraps ES queries: full-text search, filters, aggregations |
| **Orchestration** | Docker Compose | Runs MongoDB, Elasticsearch, scraper, and webapp services |

## Quick start

You need [Docker & Docker Compose](https://docs.docker.com/get-docker/). For local development outside Docker, you also need [uv](https://docs.astral.sh/uv/) and Python 3.12+.

### 1. Configure

```bash
cp .env.example .env
```

The defaults work out of the box with Docker Compose. The only things you might want to tweak are the `SCRAPE_*` variables to control how much data the spider collects. See [Configuration](#configuration) for the full list.

### 2. Run

```bash
# Start all services (Mongo + ES + scraper worker + webapp)
docker compose up -d
```

### 3. Open

The webapp is at **http://localhost:8501**.

Use the **Scraping** page in the webapp (sidebar navigation) to launch background jobs:
- **Récupérer les nouveautés** (`latest`)
- **Récupérer plus** (`backfill`)

## Webapp Scraping Helper

The project includes a dedicated helper page in Streamlit: **Scraping** (`webapp/pages/3_scraping.py`).

This helper lets you launch scraping without running manual CLI commands:
- **Récupérer les nouveautés**: incremental scan from page 1 with stop rules for already-known pages.
- **Récupérer plus**: deeper backfill to fetch older unseen ouvrages.
- **Actualiser**: refresh running/last job status.

The helper displays:
- job id, mode, status, start/end timestamps, return code
- log file path in the scraper container
- per-theme summary (`pages`, `nouveaux`, `stop reason`)

Notes:
- A `success` job can still have `Nouveaux ouvrages (run) : 0` if scanned pages only contain already-known `doc_id`.
- Log paths like `/tmp/scraper_jobs/...` are inside the `scraper` container, not your host filesystem.

## Configuration

All settings go in your `.env` file. Copy `.env.example` to get started.

| Variable | Default | Description |
|---|---|---|
| `MONGO_URI` | `mongodb://mongo:27017/cairn` | MongoDB connection string. Change `mongo` to `localhost` for local development outside Docker. |
| `ES_HOST` | `http://elasticsearch:9200` | Elasticsearch URL. Change `elasticsearch` to `localhost` for local development outside Docker. |
| `ES_INDEX` | `cairn_ouvrages` | Elasticsearch index name |
| `SCRAPER_API_URL` | `http://scraper:8000` | URL used by Streamlit to trigger background scrape jobs |
| `SCRAPE_MAX_PAGES` | `-1` (no limit) | Max listing pages to crawl per theme. Set to `3` for a quick test run. |
| `SCRAPE_MAX_ITEMS_PER_THEME` | `200` | Max books to scrape per theme. `-1` for no limit. |
| `SCRAPE_DOWNLOAD_DELAY` | `1` | Seconds to wait between requests (be nice to Cairn). |
| `SCRAPE_LATEST_MIN_PAGES` | `3` | In `latest` mode, minimum pages scanned before stop is allowed |
| `SCRAPE_LATEST_KNOWN_PAGE_STREAK` | `2` | In `latest` mode, stop after N consecutive listing pages with only known `doc_id` |
| `SCRAPE_BACKFILL_PAGES_PER_RUN` | `3` | In `backfill` mode, number of listing pages scanned per run |
| `SCRAPE_BACKFILL_MAX_NEW_ITEMS` | `50` | In `backfill` mode, maximum new ouvrages scheduled in one run (`-1` to disable) |

With the defaults (200 items per theme × 3 themes = 600 ouvrages), scraping takes about 5 minutes.

## Development

For working on the code outside Docker.

### Setup

```bash
cp .env.example .env
uv sync --group scraper --group webapp
```

Edit `.env` so the connection strings point to `localhost` instead of the Docker service names:

```
MONGO_URI=mongodb://localhost:27017/cairn
ES_HOST=http://localhost:9200
SCRAPER_API_URL=http://localhost:8000
```

### Run the scraper worker (background API)

```bash
# Start the databases + worker API
docker compose up -d mongo elasticsearch scraper
```

Or locally (outside Docker):

```bash
uv run python scripts/scraper_worker.py
```

The worker exposes:
- `POST /jobs/latest`
- `POST /jobs/backfill`
- `GET /jobs/status`

### Run a one-shot spider manually (optional)

```bash
cd scraper && uv run scrapy crawl ouvrages
```

### Run the webapp

```bash
# Make sure Elasticsearch + scraper worker are running
docker compose up -d elasticsearch scraper

# (Optional) Seed test data so you don't need to scrape first
uv run python webapp/tests/seed_fixtures.py

# Start Streamlit
uv run streamlit run webapp/app.py
```

The webapp is at **http://localhost:8501**.

## Reference

### Useful commands

```bash
# Check MongoDB data
docker exec $(docker compose ps -q mongo) mongosh cairn --eval "db.ouvrages.find().limit(3).pretty()"

# Check Elasticsearch data
curl -s 'http://localhost:9200/cairn_ouvrages/_search?pretty&size=3'

# Drop MongoDB database
docker exec $(docker compose ps -q mongo) mongosh cairn --eval "db.dropDatabase()"

# Delete Elasticsearch index
curl -X DELETE http://localhost:9200/cairn_ouvrages

# Remove everything including stored data
docker compose down -v

# Rebuild a container after code changes
docker compose build webapp
docker compose up -d webapp
```

### Project structure

```
cairn-scraping/
├── scraper/                    # Scrapy scraping module
│   ├── cairn_scraper/
│   │   ├── spiders/
│   │   │   └── ouvrages.py    # Spider: scrapes 3 themes from cairn.info
│   │   ├── items.py           # OuvrageItem: defines scraped fields
│   │   ├── pipelines.py       # MongoPipeline + ElasticsearchPipeline
│   │   └── settings.py        # Scrapy config, rate limits, DB connections
│   ├── Dockerfile             # Container for running the scraper
│   └── scrapy.cfg
│
├── webapp/                     # Streamlit web application
│   ├── app.py                 # Home page (landing + navigation)
│   ├── pages/
│   │   ├── 1_recherche.py     # Search page: full-text + faceted filters + detail dialog
│   │   ├── 2_statistiques.py  # Analytics: charts & distributions
│   │   └── 3_scraping.py      # Background scraping controls + job status
│   ├── utils/
│   │   ├── es_client.py       # ESClient: search, aggregations, get by ID
│   │   ├── scraper_client.py  # HTTP client for scraper worker API
│   │   └── components.py      # Reusable UI components (cards, filters)
│   ├── tests/
│   │   ├── fixtures.json      # Sample data for testing
│   │   └── seed_fixtures.py   # Script to seed test data into ES
│   └── Dockerfile             # Container for running the webapp
│
├── scripts/                    # Utility scripts
│   ├── bootstrap.py           # Orchestrates wait → init → crawl
│   ├── scraper_worker.py      # Background API to launch scrape jobs
│   ├── wait_for_services.py   # Health checks for MongoDB & Elasticsearch
│   └── init_es_index.py       # Creates ES index with French analyzer mapping
│
├── docker-compose.yml         # Infrastructure: MongoDB + ES + scraper + webapp
├── pyproject.toml             # Python dependencies (uv-managed)
└── .env                       # Environment configuration
```
