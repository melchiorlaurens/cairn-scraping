# cairn-scraping
E4 Data Engineering projet - Scraping cairn.info - Melchior Laurens - Kévin Feltrin

## Setup

```bash
cp .env.example .env
uv sync --group scraper
```

## Start services

```bash
docker compose up -d mongo elasticsearch
```

## Run scraper

```bash
cd scraper && uv run scrapy crawl ouvrages
```

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
