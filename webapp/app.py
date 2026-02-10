"""
Point d'entrée principal de l'application Streamlit.
Configure la page d'accueil et la navigation.
"""
import streamlit as st

# Configuration de la page
st.set_page_config(
    page_title="Cairn Ouvrages - Recherche",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded",
)

# En-tête de l'application
st.title("📚 Cairn Ouvrages")
st.markdown("### Système de recherche et d'analyse d'ouvrages académiques")

# Page d'accueil
st.markdown("""
Bienvenue dans l'application de recherche d'ouvrages Cairn.info !

Cette application vous permet de :
- 🔍 **Rechercher** des ouvrages par titre, auteur ou description
- 📖 **Consulter** les fiches détaillées des ouvrages
- 📊 **Visualiser** des statistiques sur le catalogue

Utilisez le menu latéral pour naviguer entre les différentes sections.
""")

# Statistiques rapides en sidebar
st.sidebar.title("Navigation")
st.sidebar.markdown("Utilisez les pages ci-dessus pour explorer le catalogue.")

# Informations projet
with st.sidebar.expander("ℹ️ À propos"):
    st.markdown("""
    **Projet E4 Data Engineering**
    
    Développé par :
    - Melchior Laurens (Backend)
    - Kévin Feltrin (Frontend)
    
    Technologies :
    - Scrapy (collecte)
    - MongoDB (stockage)
    - Elasticsearch (recherche)
    - Streamlit (interface)
    """)
