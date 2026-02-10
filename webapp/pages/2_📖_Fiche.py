"""
Page de fiche détaillée d'un ouvrage.
Affiche toutes les métadonnées et la description complète.
"""
import streamlit as st
import sys
from pathlib import Path

# Ajouter le dossier webapp au path pour les imports
webapp_dir = Path(__file__).parent.parent
if str(webapp_dir) not in sys.path:
    sys.path.insert(0, str(webapp_dir))

from utils.es_client import ESClient

# Initialisation du client Elasticsearch
@st.cache_resource
def get_es_client():
    return ESClient()

es_client = get_es_client()

# Récupération du doc_id depuis les paramètres d'URL
params = st.query_params
doc_id = params.get("doc_id", None)

if not doc_id:
    st.warning("Aucun ouvrage sélectionné. Retournez à la page de recherche.")
    st.stop()

# Récupération du document
doc = es_client.get_by_id(doc_id)

if not doc:
    st.error(f"Ouvrage non trouvé (ID: {doc_id})")
    st.stop()

# Affichage de la fiche
st.title("📖 Fiche Ouvrage")

# Layout en colonnes
col1, col2 = st.columns([1, 2])

with col1:
    # Image de couverture
    if doc.get("image_url"):
        try:
            st.image(doc["image_url"], use_container_width=True)
        except Exception:
            st.markdown("### 📚")
    else:
        st.markdown("### 📚")
    
    # Lien vers Cairn
    if doc.get("url"):
        st.markdown(f"[🔗 Voir sur Cairn.info]({doc['url']})")

with col2:
    # Titre et sous-titre
    title = doc.get("title", "Sans titre")
    subtitle = doc.get("subtitle", "")
    
    st.markdown(f"# {title}")
    if subtitle:
        st.markdown(f"## *{subtitle}*")
    
    # Métadonnées principales
    st.divider()
    
    # Auteurs
    authors = doc.get("authors", [])
    if authors:
        st.markdown(f"**Auteur(s) :** {', '.join(authors)}")
    
    # Éditeur et collection
    editeur = doc.get("editeur", "")
    collection = doc.get("collection", "")
    if editeur:
        st.markdown(f"**Éditeur :** {editeur}")
    if collection:
        st.markdown(f"**Collection :** {collection}")
    
    # Dates
    date_parution = doc.get("date_parution", "")
    date_mise_en_ligne = doc.get("date_mise_en_ligne", "")
    if date_parution:
        st.markdown(f"**Date de parution :** {date_parution}")
    if date_mise_en_ligne:
        st.markdown(f"**Mise en ligne :** {date_mise_en_ligne}")
    
    # ISBN et thème
    isbn = doc.get("isbn", "")
    theme = doc.get("theme", "")
    if isbn:
        st.markdown(f"**ISBN :** {isbn}")
    if theme:
        st.markdown(f"**Thème :** 🏷️ {theme}")
    
    # Prix et nombre de pages
    price = doc.get("price")
    pages = doc.get("pages")
    info = []
    if price is not None:
        info.append(f"**Prix :** {float(price):.2f} €")
    if pages is not None:
        info.append(f"**Nombre de pages :** {pages}")
    if info:
        st.markdown(" | ".join(info))

# Description complète
st.divider()
st.markdown("## 📝 Description")
description = doc.get("description", "Aucune description disponible.")
st.markdown(description)

# Bouton retour
st.divider()
if st.button("← Retour à la recherche"):
    st.switch_page("pages/1_🔍_Recherche.py")
