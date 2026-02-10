"""
Composants réutilisables pour l'interface Streamlit.
"""
import streamlit as st


def render_ouvrage_card(hit: dict) -> None:
    """
    Affiche une carte d'ouvrage dans les résultats de recherche.
    
    Args:
        hit: Document Elasticsearch (avec _id et _source)
    """
    source = hit["_source"]
    doc_id = hit["_id"]
    
    with st.container():
        col1, col2 = st.columns([1, 4])
        
        # Image de couverture
        with col1:
            if source.get("image_url"):
                try:
                    st.image(source["image_url"], use_container_width=True)
                except Exception:
                    st.markdown("📚")
            else:
                st.markdown("📚")
        
        # Informations de l'ouvrage
        with col2:
            # Titre cliquable
            title = source.get("title", "Sans titre")
            subtitle = source.get("subtitle", "")
            
            st.markdown(f"### {title}")
            if subtitle:
                st.markdown(f"*{subtitle}*")
            
            # Métadonnées
            authors = source.get("authors", [])
            if authors:
                st.markdown(f"**Auteur(s) :** {', '.join(authors)}")
            
            editeur = source.get("editeur", "")
            date_parution = source.get("date_parution", "")
            if editeur or date_parution:
                info = []
                if editeur:
                    info.append(f"**Éditeur :** {editeur}")
                if date_parution:
                    info.append(f"**Date :** {date_parution}")
                st.markdown(" | ".join(info))
            
            # Prix et pages
            price = source.get("price")
            pages = source.get("pages")
            if price is not None or pages is not None:
                info = []
                if price is not None:
                    info.append(f"**Prix :** {float(price):.2f} €")
                if pages is not None:
                    info.append(f"**Pages :** {pages}")
                st.markdown(" | ".join(info))
            
            # Theme + lien vers fiche
            col_theme, col_btn = st.columns([3, 1])
            with col_theme:
                theme = source.get("theme", "")
                if theme:
                    st.markdown(f"🏷️ {theme}")
            with col_btn:
                st.link_button("📖 Voir la fiche", f"/Fiche?doc_id={doc_id}")
        
        st.divider()


def render_sidebar_filters(
    themes: list[dict],
    editeurs: list[dict],
    collections: list[dict],
    auteurs: list[dict],
) -> dict:
    """
    Affiche les filtres dans la sidebar et retourne les valeurs sélectionnées.
    
    Args:
        themes: Liste des buckets de thèmes
        editeurs: Liste des buckets d'éditeurs
        collections: Liste des buckets de collections
        auteurs: Liste des buckets d'auteurs
        
    Returns:
        Dictionnaire des filtres sélectionnés
    """
    st.sidebar.markdown("## 🔍 Filtres")
    
    filters = {}
    
    # Filtre par thème
    if themes:
        theme_options = ["Tous"] + [bucket["key"] for bucket in themes]
        selected_theme = st.sidebar.selectbox(
            "Thème",
            theme_options,
            key="filter_theme"
        )
        if selected_theme != "Tous":
            filters["theme"] = [selected_theme]
    
    # Filtre par éditeur
    if editeurs:
        editeur_options = [f"{bucket['key']} ({bucket['doc_count']})" for bucket in editeurs[:10]]
        selected_editeurs = st.sidebar.multiselect(
            "Éditeur",
            editeur_options,
            key="filter_editeur"
        )
        if selected_editeurs:
            # Extraire juste le nom (avant le compteur)
            filters["editeur"] = [opt.split(" (")[0] for opt in selected_editeurs]
    
    # Filtre par collection
    if collections:
        collection_options = [f"{bucket['key']} ({bucket['doc_count']})" for bucket in collections[:10]]
        selected_collections = st.sidebar.multiselect(
            "Collection",
            collection_options,
            key="filter_collection"
        )
        if selected_collections:
            filters["collection"] = [opt.split(" (")[0] for opt in selected_collections]
    
    # Filtre par auteur
    if auteurs:
        auteur_options = [f"{bucket['key']} ({bucket['doc_count']})" for bucket in auteurs[:20]]
        selected_auteurs = st.sidebar.multiselect(
            "Auteur",
            auteur_options,
            key="filter_auteur"
        )
        if selected_auteurs:
            filters["authors"] = [opt.split(" (")[0] for opt in selected_auteurs]
    
    return filters


def render_pagination(total: int, page: int, size: int) -> int:
    """
    Affiche les contrôles de pagination et retourne la nouvelle page.
    
    Args:
        total: Nombre total de résultats
        page: Page actuelle
        size: Résultats par page
        
    Returns:
        Nouvelle page sélectionnée
    """
    total_pages = (total + size - 1) // size  # Arrondi supérieur
    
    if total_pages <= 1:
        return page
    
    col1, col2, col3, col4, col5 = st.columns([1, 1, 2, 1, 1])
    
    new_page = page
    
    with col1:
        if st.button("⏮️ Début", disabled=(page == 1)):
            new_page = 1
    
    with col2:
        if st.button("◀️ Précédent", disabled=(page == 1)):
            new_page = page - 1
    
    with col3:
        st.markdown(f"<div style='text-align: center; padding: 5px;'>Page {page} / {total_pages}</div>", unsafe_allow_html=True)
    
    with col4:
        if st.button("Suivant ▶️", disabled=(page >= total_pages)):
            new_page = page + 1
    
    with col5:
        if st.button("Fin ⏭️", disabled=(page >= total_pages)):
            new_page = total_pages
    
    return new_page
