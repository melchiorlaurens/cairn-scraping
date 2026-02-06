import logging
from urllib.parse import urlparse

from itemadapter import ItemAdapter
from pymongo import MongoClient, ReplaceOne
from elasticsearch import Elasticsearch

logger = logging.getLogger(__name__)


class MongoPipeline:
    def __init__(self, mongo_uri):
        self.mongo_uri = mongo_uri

    @classmethod
    def from_crawler(cls, crawler):
        return cls(mongo_uri=crawler.settings.get("MONGO_URI"))

    def open_spider(self):
        parsed = urlparse(self.mongo_uri)
        db_name = parsed.path.lstrip("/") or "cairn"
        self.client = MongoClient(self.mongo_uri)
        self.db = self.client[db_name]
        self.collection = self.db["ouvrages"]
        logger.info("MongoPipeline connected to %s / %s", self.mongo_uri, db_name)

    def close_spider(self):
        self.client.close()

    def process_item(self, item):
        adapter = ItemAdapter(item)
        doc = adapter.asdict()
        self.collection.replace_one(
            {"doc_id": doc["doc_id"]},
            doc,
            upsert=True,
        )
        return item


class ElasticsearchPipeline:
    def __init__(self, es_host, es_index):
        self.es_host = es_host
        self.es_index = es_index

    @classmethod
    def from_crawler(cls, crawler):
        return cls(
            es_host=crawler.settings.get("ES_HOST"),
            es_index=crawler.settings.get("ES_INDEX"),
        )

    def open_spider(self):
        self.es = Elasticsearch(self.es_host)
        logger.info("ElasticsearchPipeline connected to %s", self.es_host)

    def close_spider(self):
        self.es.close()

    def process_item(self, item):
        adapter = ItemAdapter(item)
        doc = adapter.asdict()
        self.es.index(
            index=self.es_index,
            id=doc["doc_id"],
            document=doc,
        )
        return item
