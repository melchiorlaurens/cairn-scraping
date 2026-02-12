"""
Page de statistiques et visualisations.
Affiche des graphiques sur le catalogue d'ouvrages.
"""
import streamlit as st
import sys
from pathlib import Path
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# Ajouter le dossier webapp au path pour les imports
webapp_dir = Path(__file__).parent.parent
if str(webapp_dir) not in sys.path:
    sys.path.insert(0, str(webapp_dir))

from utils.es_client import ESClient

# Titre
st.title("📊 Statistiques du catalogue")

# Initialisation du client Elasticsearch
@st.cache_resource
def get_es_client():
    return ESClient()

es_client = get_es_client()

# Récupération des agrégations
aggs = es_client.get_aggregations()

# Nombre total d'ouvrages
total = es_client.get_count()
st.metric("Nombre total d'ouvrages", total)

st.divider()

# === GRAPHIQUES ===

# 1. Distribution par thème (Pie Chart)
st.markdown("### 📚 Répartition par thème")
if aggs["themes"]:
    themes_df = pd.DataFrame(aggs["themes"])
    fig_themes = px.pie(
        themes_df,
        values="doc_count",
        names="key",
        title="Distribution des ouvrages par thème",
        hole=0.3,  # Donut chart
    )
    st.plotly_chart(fig_themes, use_container_width=True)
else:
    st.info("Aucune donnée de thème disponible.")

st.divider()

# 2. Top 10 éditeurs (Bar Chart)
st.markdown("### 🏢 Top 10 des éditeurs")
if aggs["editeurs"]:
    editeurs_df = pd.DataFrame(aggs["editeurs"][:10])
    fig_editeurs = px.bar(
        editeurs_df,
        x="doc_count",
        y="key",
        orientation="h",
        title="Nombre d'ouvrages par éditeur",
        labels={"doc_count": "Nombre d'ouvrages", "key": "Éditeur"},
        color="doc_count",
        color_continuous_scale="Blues",
    )
    fig_editeurs.update_layout(yaxis={'categoryorder':'total ascending'})
    st.plotly_chart(fig_editeurs, use_container_width=True)
else:
    st.info("Aucune donnée d'éditeur disponible.")

st.divider()

# 3. Distribution des prix (Histogram)
st.markdown("### 💰 Distribution des prix")
if aggs["prix_histogram"]:
    prix_df = pd.DataFrame(aggs["prix_histogram"])
    prix_df["key"] = prix_df["key"].astype(float)

    fig_prix = px.bar(
        prix_df,
        x="key",
        y="doc_count",
        title="Répartition par tranche de prix (10€)",
        labels={"key": "Prix (€)", "doc_count": "Nombre d'ouvrages"},
        color="doc_count",
        color_continuous_scale="Greens",
    )
    st.plotly_chart(fig_prix, use_container_width=True)
else:
    st.info("Aucune donnée de prix disponible.")

st.divider()

# 4. Distribution du nombre de pages
st.markdown("### 📄 Distribution du nombre de pages")
if aggs["pages_histogram"]:
    pages_df = pd.DataFrame(aggs["pages_histogram"])
    pages_df["key"] = pages_df["key"].astype(int)

    fig_pages = px.bar(
        pages_df,
        x="key",
        y="doc_count",
        title="Répartition par tranche de pages (100 p.)",
        labels={"key": "Nombre de pages", "doc_count": "Nombre d'ouvrages"},
        color="doc_count",
        color_continuous_scale="Oranges",
    )
    st.plotly_chart(fig_pages, use_container_width=True)
else:
    st.info("Aucune donnée de pages disponible.")

st.divider()

# 4. Évolution temporelle (Line Chart)
st.markdown("### 📅 Évolution des publications par année")
if aggs["annees"]:
    annees_df = pd.DataFrame(aggs["annees"])
    annees_df["key"] = pd.to_datetime(annees_df["key"], unit="ms")
    annees_df = annees_df.sort_values("key")
    
    fig_annees = px.line(
        annees_df,
        x="key",
        y="doc_count",
        title="Nombre d'ouvrages publiés par année",
        labels={"key": "Année", "doc_count": "Nombre d'ouvrages"},
        markers=True,
    )
    fig_annees.update_traces(line_color="#1f77b4", line_width=3)
    st.plotly_chart(fig_annees, use_container_width=True)
else:
    st.info("Aucune donnée temporelle disponible.")

st.divider()

# 5. Top collections
st.markdown("### 📖 Collections les plus fournies")
if aggs["collections"]:
    collections_df = pd.DataFrame(aggs["collections"][:15])
    
    fig_collections = go.Figure(go.Bar(
        x=collections_df["doc_count"],
        y=collections_df["key"],
        orientation='h',
        marker=dict(
            color=collections_df["doc_count"],
            colorscale='Viridis',
        )
    ))
    
    fig_collections.update_layout(
        title="Top 15 des collections",
        xaxis_title="Nombre d'ouvrages",
        yaxis_title="Collection",
        yaxis={'categoryorder':'total ascending'},
        height=500,
    )
    
    st.plotly_chart(fig_collections, use_container_width=True)
else:
    st.info("Aucune donnée de collection disponible.")

st.divider()

# 6. Top auteurs
st.markdown("### ✍️ Auteurs les plus prolifiques")
if aggs["auteurs"]:
    auteurs_df = pd.DataFrame(aggs["auteurs"][:20])
    
    fig_auteurs = px.bar(
        auteurs_df,
        x="doc_count",
        y="key",
        orientation="h",
        title="Top 20 des auteurs par nombre d'ouvrages",
        labels={"doc_count": "Nombre d'ouvrages", "key": "Auteur"},
        color="doc_count",
        color_continuous_scale="Purples",
    )
    fig_auteurs.update_layout(
        yaxis={'categoryorder': 'total ascending'},
        height=500,
    )
    
    st.plotly_chart(fig_auteurs, use_container_width=True)
else:
    st.info("Aucune donnée d'auteur disponible.")
