"""
Client Elasticsearch pour l'application Streamlit.
Fournit les méthodes de recherche, récupération et agrégation.
"""
import os
from typing import Optional
from elasticsearch import Elasticsearch


class ESClient:
    """Client pour interagir avec Elasticsearch."""
    
    def __init__(
        self, 
        host: str = None,
        index: str = None
    ):
        """
        Initialise le client Elasticsearch.
        
        Args:
            host: URL du serveur Elasticsearch (par défaut depuis .env)
            index: Nom de l'index à utiliser (par défaut depuis .env)
        """
        self.host = host or os.getenv("ES_HOST", "http://localhost:9200")
        self.index = index or os.getenv("ES_INDEX", "cairn_ouvrages")
        self.es = Elasticsearch(self.host)
        
    def search(
        self,
        query: str = "",
        filters: Optional[dict[str, list[str]]] = None,
        page: int = 1,
        size: int = 20,
    ) -> dict:
        """
        Recherche des ouvrages avec filtres et pagination.
        
        Args:
            query: Texte de recherche (titre, description, auteurs)
            filters: Dictionnaire de filtres par facettes
                     ex: {"theme": ["SHS"], "editeur": ["PUF"]}
            page: Numéro de page (commence à 1)
            size: Nombre de résultats par page
            
        Returns:
            Dictionnaire avec 'total' et 'hits' (liste de documents)
        """
        # Calcul de l'offset pour la pagination
        from_offset = (page - 1) * size
        
        # Construction de la query
        must_clauses = []
        filter_clauses = []
        
        # Recherche textuelle si une query est fournie
        if query:
            must_clauses.append({
                "multi_match": {
                    "query": query,
                    "fields": ["title^3", "subtitle^2", "description", "authors"],
                    "type": "best_fields",
                    "fuzziness": "AUTO"
                }
            })
        
        # Ajout des filtres par facettes
        if filters:
            for field, values in filters.items():
                if values:  # Seulement si la liste n'est pas vide
                    filter_clauses.append({
                        "terms": {field: values}
                    })
        
        # Construction du body de la requête
        body = {
            "from": from_offset,
            "size": size,
            "query": {
                "bool": {
                    "must": must_clauses if must_clauses else [{"match_all": {}}],
                    "filter": filter_clauses
                }
            },
            "sort": [
                {"_score": {"order": "desc"}},
                {"date_parution": {"order": "desc"}}
            ]
        }
        
        try:
            response = self.es.search(index=self.index, body=body)
            return {
                "total": response["hits"]["total"]["value"],
                "hits": response["hits"]["hits"]
            }
        except Exception as e:
            print(f"Erreur lors de la recherche : {e}")
            return {"total": 0, "hits": []}
    
    def get_by_id(self, doc_id: str) -> Optional[dict]:
        """
        Récupère un ouvrage par son ID.
        
        Args:
            doc_id: Identifiant unique du document
            
        Returns:
            Document complet ou None si non trouvé
        """
        try:
            response = self.es.get(index=self.index, id=doc_id)
            return response["_source"]
        except Exception as e:
            print(f"Erreur lors de la récupération du document {doc_id} : {e}")
            return None
    
    def get_aggregations(
        self,
        filters: Optional[dict[str, list[str]]] = None,
    ) -> dict:
        """
        Récupère les agrégations pour les statistiques et facettes.
        
        Args:
            filters: Filtres à appliquer avant agrégation
            
        Returns:
            Dictionnaire avec les buckets pour chaque agrégation :
            - themes: liste de {key, doc_count}
            - editeurs: liste de {key, doc_count}
            - collections: liste de {key, doc_count}
            - auteurs: liste de {key, doc_count}
            - prix_histogram: liste de {key, doc_count}
            - pages_histogram: liste de {key, doc_count}
            - annees: liste de {key, doc_count}
        """
        # Construction des filtres
        filter_clauses = []
        if filters:
            for field, values in filters.items():
                if values:
                    filter_clauses.append({
                        "terms": {field: values}
                    })
        
        # Body de la requête avec toutes les agrégations
        body = {
            "size": 0,  # On ne veut que les agrégations, pas les documents
            "query": {
                "bool": {
                    "filter": filter_clauses
                }
            } if filter_clauses else {"match_all": {}},
            "aggs": {
                "themes": {
                    "terms": {"field": "theme", "size": 10}
                },
                "editeurs": {
                    "terms": {"field": "editeur", "size": 20}
                },
                "collections": {
                    "terms": {"field": "collection", "size": 30}
                },
                "auteurs": {
                    "terms": {"field": "authors", "size": 50}
                },
                "prix_histogram": {
                    "histogram": {
                        "field": "price",
                        "interval": 10,
                        "min_doc_count": 1
                    }
                },
                "pages_histogram": {
                    "histogram": {
                        "field": "pages",
                        "interval": 100,
                        "min_doc_count": 1
                    }
                },
                "annees": {
                    "date_histogram": {
                        "field": "date_parution",
                        "calendar_interval": "year",
                        "format": "yyyy",
                        "min_doc_count": 1
                    }
                }
            }
        }
        
        try:
            response = self.es.search(index=self.index, body=body)
            aggs = response["aggregations"]
            
            return {
                "themes": aggs["themes"]["buckets"],
                "editeurs": aggs["editeurs"]["buckets"],
                "collections": aggs["collections"]["buckets"],
                "auteurs": aggs["auteurs"]["buckets"],
                "prix_histogram": aggs["prix_histogram"]["buckets"],
                "pages_histogram": aggs["pages_histogram"]["buckets"],
                "annees": aggs["annees"]["buckets"],
            }
        except Exception as e:
            print(f"Erreur lors de la récupération des agrégations : {e}")
            return {
                "themes": [],
                "editeurs": [],
                "collections": [],
                "auteurs": [],
                "prix_histogram": [],
                "pages_histogram": [],
                "annees": [],
            }
    
    def get_count(self) -> int:
        """
        Retourne le nombre total de documents dans l'index.
        
        Returns:
            Nombre total d'ouvrages
        """
        try:
            response = self.es.count(index=self.index)
            return response["count"]
        except Exception as e:
            print(f"Erreur lors du comptage : {e}")
            return 0
