"""
Script pour injecter les fixtures dans Elasticsearch pour le développement.
Permet de travailler sur le frontend sans attendre le scraping complet.
"""
import json
from pathlib import Path
from elasticsearch import Elasticsearch

# Configuration
ES_HOST = "http://localhost:9200"
ES_INDEX = "cairn_ouvrages"

def main():
    """Crée l'index et injecte les données de test."""
    
    # Connexion à Elasticsearch
    es = Elasticsearch(ES_HOST)
    
    # Supprimer l'index s'il existe déjà
    if es.indices.exists(index=ES_INDEX):
        print(f"Suppression de l'index existant '{ES_INDEX}'...")
        es.indices.delete(index=ES_INDEX)
    
    # Créer l'index avec le mapping approprié
    print(f"Création de l'index '{ES_INDEX}'...")
    mapping = {
        "mappings": {
            "properties": {
                "title": {"type": "text", "analyzer": "french"},
                "subtitle": {"type": "text", "analyzer": "french"},
                "authors": {"type": "keyword"},
                "collection": {"type": "keyword"},
                "editeur": {"type": "keyword"},
                "date_parution": {"type": "date", "format": "yyyy-MM-dd||yyyy"},
                "date_mise_en_ligne": {"type": "date", "format": "yyyy-MM-dd||yyyy"},
                "pages": {"type": "integer"},
                "price": {"type": "float"},
                "description": {"type": "text", "analyzer": "french"},
                "isbn": {"type": "keyword"},
                "theme": {"type": "keyword"},
                "image_url": {"type": "keyword", "index": False},
                "url": {"type": "keyword", "index": False},
                "doc_id": {"type": "keyword"}
            }
        }
    }
    
    es.indices.create(index=ES_INDEX, body=mapping)
    
    # Charger les fixtures
    fixtures_path = Path(__file__).parent / "fixtures.json"
    print(f"Chargement des fixtures depuis {fixtures_path}...")
    
    with open(fixtures_path, "r", encoding="utf-8") as f:
        fixtures = json.load(f)
    
    # Indexer chaque document
    print(f"Indexation de {len(fixtures)} documents...")
    for doc in fixtures:
        es.index(index=ES_INDEX, id=doc["doc_id"], document=doc)
    
    # Rafraîchir l'index pour rendre les documents immédiatement disponibles
    es.indices.refresh(index=ES_INDEX)
    
    print(f"✅ {len(fixtures)} documents indexés avec succès dans '{ES_INDEX}'")
    
    # Vérification
    count = es.count(index=ES_INDEX)
    print(f"📊 Nombre total de documents dans l'index : {count['count']}")

if __name__ == "__main__":
    main()
