# Dockerfile pour l'application Streamlit
FROM python:3.12-slim

WORKDIR /app

# Installer uv pour la gestion des dépendances
RUN pip install --no-cache-dir uv

# Copier les fichiers de configuration
COPY pyproject.toml uv.lock ./

# Installer les dépendances webapp
RUN uv sync --group webapp --no-dev

# Copier le code de l'application
COPY webapp/ ./webapp/

# Exposer le port Streamlit
EXPOSE 8501

# Variables d'environnement par défaut
ENV ES_HOST=http://elasticsearch:9200
ENV ES_INDEX=cairn_ouvrages

# Lancer l'application Streamlit
CMD ["uv", "run", "streamlit", "run", "webapp/app.py", "--server.address", "0.0.0.0"]
