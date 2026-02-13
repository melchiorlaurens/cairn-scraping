"""Page de pilotage du scraping en arriere-plan."""

import sys
from pathlib import Path

import streamlit as st

# Ajouter le dossier webapp au path pour les imports
webapp_dir = Path(__file__).parent.parent
if str(webapp_dir) not in sys.path:
    sys.path.insert(0, str(webapp_dir))

from utils.scraper_client import ScraperClient


@st.cache_resource
def get_scraper_client():
    return ScraperClient()


def render_job_block(title, job):
    st.markdown(f"### {title}")
    if not job:
        st.info("Aucune information disponible.")
        return

    st.markdown(f"**ID job :** `{job.get('job_id', 'inconnu')}`")
    st.markdown(f"**Mode :** `{job.get('mode', 'inconnu')}`")
    st.markdown(f"**Statut :** `{job.get('status', 'inconnu')}`")

    started_at = job.get("started_at", "")
    ended_at = job.get("ended_at", "")
    if started_at:
        st.markdown(f"**Debut :** {started_at}")
    if ended_at:
        st.markdown(f"**Fin :** {ended_at}")

    return_code = job.get("return_code")
    if return_code is not None:
        st.markdown(f"**Code retour :** `{return_code}`")

    error_message = job.get("error", "")
    if error_message:
        st.error(error_message)

    log_path = job.get("log_path", "")
    if log_path:
        st.markdown(f"**Log :** `{log_path}`")

    summary = job.get("summary")
    if summary:
        st.markdown("#### Resume")
        st.markdown(f"**Nouveaux ouvrages (run) :** {summary.get('total_new_items_scraped', 0)}")

        themes = summary.get("themes", {})
        if themes:
            for theme_name, values in themes.items():
                st.markdown(f"- **{theme_name}**: pages={values.get('pages_scanned', 0)}, nouveaux={values.get('new_items_scraped', 0)}, stop={values.get('stopped_reason', '')}")


st.title("🛠️ Scraping en arriere-plan")
st.markdown(
    """
    Lancez des jobs sans bloquer l'interface :
    - **Recuperer les nouveautes** : repart de la page 1 et s'arrete avec la regle de pages connues consecutives.
    - **Recuperer plus** : continue plus profond dans l'historique avec un pas fixe.
    """
)

client = get_scraper_client()

col1, col2, col3 = st.columns([2, 2, 1])
with col1:
    if st.button("🔄 Recuperer les nouveautes", use_container_width=True):
        response = client.start_latest()
        if response["ok"]:
            st.success("Job 'latest' lance.")
        else:
            message = response["data"].get("error") or response["error"]
            st.error(f"Echec du lancement: {message}")

with col2:
    if st.button("📚 Recuperer plus", use_container_width=True):
        response = client.start_backfill()
        if response["ok"]:
            st.success("Job 'backfill' lance.")
        else:
            message = response["data"].get("error") or response["error"]
            st.error(f"Echec du lancement: {message}")

with col3:
    if st.button("Actualiser", use_container_width=True):
        st.rerun()

status_response = client.get_status()
if not status_response["ok"]:
    st.error(f"Worker indisponible: {status_response['error']}")
else:
    payload = status_response["data"]
    running = payload.get("running", False)
    if running:
        st.warning("Un job est en cours.")
    else:
        st.info("Aucun job en cours.")

    render_job_block("Job en cours", payload.get("current_job"))
    st.divider()
    render_job_block("Dernier job termine", payload.get("last_job"))
