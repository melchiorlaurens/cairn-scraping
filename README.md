# cairn-scraping

E4 Data Engineering projet — Scraping [cairn.info](https://cairn.info) — Melchior Laurens & Kévin Feltrin

Scrapy spider that collects academic books from Cairn.info, stores them in **MongoDB** and **Elasticsearch**, and exposes them through a **Streamlit** webapp with search, detail views, and statistics dashboards.

## Project Structure

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

## Architecture Overview

The project follows a classic **ETL** pipeline with a search & visualization layer:

**Cairn.info** → **Scrapy spider** → **MongoDB** + **Elasticsearch** → **Streamlit webapp**

The `OuvragesSpider` scrapes book metadata (title, authors, ISBN, description, price, publisher, collection, dates, page count) across 3 Cairn themes: *Sciences humaines et sociales*, *Sciences et techniques*, and *Droit*. Each scraped item is then passed through two pipelines in parallel: **MongoDB** for persistent raw storage, and **Elasticsearch** (with a French text analyzer) for full-text search, faceted filtering, and aggregations. The **Streamlit webapp** queries Elasticsearch to provide search, detail views, and statistics dashboards powered by Plotly.

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

## Prerequisites

- [Docker & Docker Compose](https://docs.docker.com/get-docker/)
- [uv](https://docs.astral.sh/uv/) (only for local development)
- Python 3.12+ (only for local development)

## Quick start (Docker)

The fastest way to get everything running:

```bash
# 1. Create your env file
cp .env.example .env

# 2. Start the infrastructure
docker compose up -d mongo elasticsearch

# 3. Run the scraper (waits for services, creates index, then crawls)
docker compose up scraper

# 4. Start the webapp
docker compose up -d webapp
```

The webapp is available at **http://localhost:8501**.

## Local development

### Setup

```bash
cp .env.example .env
uv sync --group scraper --group webapp
```

### Run the scraper locally

```bash
# Start the infrastructure
docker compose up -d mongo elasticsearch

# Launch the spider
cd scraper && uv run scrapy crawl ouvrages
```

### Run the webapp locally

```bash
# Make sure Elasticsearch is running
docker compose up -d elasticsearch

# (Optional) Seed test data so you don't need to scrape first
uv run python webapp/tests/seed_fixtures.py

# Start Streamlit
uv run streamlit run webapp/app.py
```

The webapp is available at **http://localhost:8501**.

### Rebuild the webapp
```
docker compose build webapp
docker compose up -d webapp
```


## Environment variables

| Variable | Default | Description |
|---|---|---|
| `MONGO_URI` | `mongodb://mongo:27017/cairn` | MongoDB connection string |
| `ES_HOST` | `http://elasticsearch:9200` | Elasticsearch URL |
| `ES_INDEX` | `cairn_ouvrages` | Elasticsearch index name |

## Verify data

```bash
# MongoDB
docker exec $(docker compose ps -q mongo) mongosh cairn --eval "db.ouvrages.find().limit(3).pretty()"

# Elasticsearch
curl -s 'http://localhost:9200/cairn_ouvrages/_search?pretty&size=3'
```

## Clean data

```bash
# Drop MongoDB database
docker exec $(docker compose ps -q mongo) mongosh cairn --eval "db.dropDatabase()"

# Delete Elasticsearch index
curl -X DELETE http://localhost:9200/cairn_ouvrages

# Or nuke everything (removes volumes)
docker compose down -v
```
