"""Wait for MongoDB and Elasticsearch to be ready."""

import os
import time

from pymongo import MongoClient
from pymongo.errors import ConnectionFailure
from elasticsearch import Elasticsearch


MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/cairn")
ES_HOST = os.getenv("ES_HOST", "http://localhost:9200")
MAX_RETRIES = 30
RETRY_INTERVAL = 2


def wait_mongo():
    client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=2000)
    for i in range(MAX_RETRIES):
        try:
            client.admin.command("ping")
            print("MongoDB is ready.")
            client.close()
            return
        except ConnectionFailure:
            print(f"Waiting for MongoDB... ({i + 1}/{MAX_RETRIES})")
            time.sleep(RETRY_INTERVAL)
    raise RuntimeError("MongoDB did not become ready in time.")


def wait_es():
    es = Elasticsearch(ES_HOST, request_timeout=2)
    for i in range(MAX_RETRIES):
        try:
            if es.ping():
                print("Elasticsearch is ready.")
                es.close()
                return
        except Exception:
            pass
        print(f"Waiting for Elasticsearch... ({i + 1}/{MAX_RETRIES})")
        time.sleep(RETRY_INTERVAL)
    raise RuntimeError("Elasticsearch did not become ready in time.")


if __name__ == "__main__":
    wait_mongo()
    wait_es()
    print("All services are ready.")
