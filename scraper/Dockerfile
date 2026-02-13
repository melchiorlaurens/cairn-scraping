FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

# Install dependencies
COPY pyproject.toml uv.lock ./
RUN uv sync --group scraper --no-dev --frozen

# Copy source
COPY scripts/ scripts/
COPY scraper/ scraper/

ENV PYTHONPATH=/app/scripts
CMD ["uv", "run", "python", "scripts/scraper_worker.py"]
