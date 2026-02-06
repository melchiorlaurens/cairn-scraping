"""Create the Elasticsearch index with an explicit mapping."""

import os

from elasticsearch import Elasticsearch

ES_HOST = os.getenv("ES_HOST", "http://localhost:9200")
ES_INDEX = os.getenv("ES_INDEX", "cairn_ouvrages")

MAPPING = {
    "mappings": {
        "properties": {
            "title":              {"type": "text", "analyzer": "french"},
            "subtitle":           {"type": "text", "analyzer": "french"},
            "authors":            {"type": "keyword"},
            "collection":         {"type": "keyword"},
            "editeur":            {"type": "keyword"},
            "date_parution":      {"type": "date", "format": "dd/MM/yyyy||yyyy-MM-dd||yyyy"},
            "date_mise_en_ligne": {"type": "date", "format": "dd/MM/yyyy||yyyy-MM-dd||yyyy"},
            "pages":              {"type": "integer"},
            "price":              {"type": "float"},
            "description":        {"type": "text", "analyzer": "french"},
            "isbn":               {"type": "keyword"},
            "theme":              {"type": "keyword"},
            "image_url":          {"type": "keyword", "index": False},
            "url":                {"type": "keyword", "index": False},
            "doc_id":             {"type": "keyword"},
        }
    }
}


def main():
    es = Elasticsearch(ES_HOST)
    if es.indices.exists(index=ES_INDEX):
        print(f"Index '{ES_INDEX}' already exists — skipping creation.")
    else:
        es.indices.create(index=ES_INDEX, body=MAPPING)
        print(f"Index '{ES_INDEX}' created.")
    es.close()


if __name__ == "__main__":
    main()
