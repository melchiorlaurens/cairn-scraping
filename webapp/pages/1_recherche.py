"""
Page de recherche d'ouvrages.
Permet de rechercher par texte et de filtrer par facettes.
"""
import streamlit as st
import sys
from pathlib import Path

# Ajouter le dossier webapp au path pour les imports
webapp_dir = Path(__file__).parent.parent
if str(webapp_dir) not in sys.path:
    sys.path.insert(0, str(webapp_dir))

from utils.es_client import ESClient
from utils.components import render_ouvrage_card, render_sidebar_filters, render_pagination

# Titre
st.title("🔍 Recherche d'ouvrages")

# Initialisation du client Elasticsearch
@st.cache_resource
def get_es_client():
    return ESClient()

es_client = get_es_client()

# Initialisation du session state pour la pagination
if "search_page" not in st.session_state:
    st.session_state.search_page = 1

if "search_query" not in st.session_state:
    st.session_state.search_query = ""

# Barre de recherche
query = st.text_input(
    "Rechercher par titre, auteur ou description",
    value=st.session_state.search_query,
    placeholder="Ex: sociologie, droit constitutionnel, Pierre Durand...",
    key="search_input"
)

# Si la query change, réinitialiser la page
if query != st.session_state.search_query:
    st.session_state.search_query = query
    st.session_state.search_page = 1

# Récupérer les agrégations pour les filtres
aggs = es_client.get_aggregations()

# Afficher les filtres dans la sidebar
filters = render_sidebar_filters(
    themes=aggs["themes"],
    editeurs=aggs["editeurs"],
    collections=aggs["collections"],
    auteurs=aggs["auteurs"],
)

# Affichage du nombre total d'ouvrages
total_count = es_client.get_count()
st.sidebar.markdown(f"**Total d'ouvrages :** {total_count}")

# Bouton de réinitialisation des filtres
if st.sidebar.button("🔄 Réinitialiser les filtres"):
    st.session_state.search_page = 1
    st.rerun()

# Recherche avec pagination
page = st.session_state.search_page
size = 20

results = es_client.search(
    query=query,
    filters=filters,
    page=page,
    size=size,
)

# Affichage des résultats
total = results["total"]
hits = results["hits"]

if total == 0:
    st.info("Aucun résultat trouvé. Essayez de modifier votre recherche ou vos filtres.")
else:
    # Informations sur les résultats
    start = (page - 1) * size + 1
    end = min(page * size, total)
    st.markdown(f"**{total} résultat(s) trouvé(s)** — Affichage de {start} à {end}")
    
    # Affichage des cartes d'ouvrages
    for hit in hits:
        render_ouvrage_card(hit)
    
    # Pagination
    new_page = render_pagination(total, page, size)
    if new_page != page:
        st.session_state.search_page = new_page
        st.rerun()
