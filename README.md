# cairn-scraping

E4 Data Engineering projet — Scraping [cairn.info](https://cairn.info) — Melchior Laurens & Kévin Feltrin

Scrapy spider that collects academic books from Cairn.info, stores them in **MongoDB** and **Elasticsearch**, and exposes them through a **Streamlit** webapp with search, detail views, and statistics dashboards.

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

### Key Components

| Component | Technology | Purpose |
|-----------|------------|---------|
| **Spider** | Scrapy | Crawls cairn.info, extracts book metadata |
| **Pipelines** | pymongo + elasticsearch-py | Dual storage: MongoDB (backup) + ES (search) |
| **Index mapping** | Elasticsearch | French analyzer for titles/descriptions, keyword fields for filters |
| **Web app** | Streamlit | Interactive search UI with facets and analytics dashboard |
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
# Start the infrastructure and the webapp
docker compose up -d mongo elasticsearch webapp

# Run the spider (waits for services, creates the ES index, then crawls)
docker compose up scraper
```

### 3. Open

The webapp is at **http://localhost:8501**.

## Configuration

All settings go in your `.env` file. Copy `.env.example` to get started.

| Variable | Default | Description |
|---|---|---|
| `MONGO_URI` | `mongodb://mongo:27017/cairn` | MongoDB connection string. Change `mongo` to `localhost` for local development outside Docker. |
| `ES_HOST` | `http://elasticsearch:9200` | Elasticsearch URL. Change `elasticsearch` to `localhost` for local development outside Docker. |
| `ES_INDEX` | `cairn_ouvrages` | Elasticsearch index name |
| `SCRAPE_MAX_PAGES` | `-1` (no limit) | Max listing pages to crawl per theme. Set to `3` for a quick test run. |
| `SCRAPE_MAX_ITEMS_PER_THEME` | `200` | Max books to scrape per theme. `-1` for no limit. |
| `SCRAPE_DOWNLOAD_DELAY` | `1` | Seconds to wait between requests (be nice to Cairn). |

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
```

### Run the scraper

```bash
# Start the databases
docker compose up -d mongo elasticsearch

# Launch the spider
cd scraper && uv run scrapy crawl ouvrages
```

### Run the webapp

```bash
# Make sure Elasticsearch is running
docker compose up -d elasticsearch

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
│   │   ├── 1_recherche.py     # Search page: full-text + faceted filters
│   │   ├── 2_fiche.py         # Detail view: complete book metadata
│   │   └── 3_statistiques.py  # Analytics: charts & distributions
│   ├── utils/
│   │   ├── es_client.py       # ESClient: search, aggregations, get by ID
│   │   └── components.py      # Reusable UI components (cards, filters)
│   ├── tests/
│   │   ├── fixtures.json      # Sample data for testing
│   │   └── seed_fixtures.py   # Script to seed test data into ES
│   └── Dockerfile             # Container for running the webapp
│
├── scripts/                    # Utility scripts
│   ├── bootstrap.py           # Orchestrates wait → init → crawl
│   ├── wait_for_services.py   # Health checks for MongoDB & Elasticsearch
│   └── init_es_index.py       # Creates ES index with French analyzer mapping
│
├── docker-compose.yml         # Infrastructure: MongoDB + ES + scraper + webapp
├── pyproject.toml             # Python dependencies (uv-managed)
└── .env                       # Environment configuration
```
