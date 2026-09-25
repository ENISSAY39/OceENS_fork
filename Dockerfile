FROM python:3.12-slim
COPY --from=ghcr.io/astral-sh/uv:0.11.32 /uv /uvx /bin/
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 \
    UV_LINK_MODE=copy UV_PYTHON_DOWNLOADS=never

RUN apt-get update && apt-get install -y --no-install-recommends curl ca-certificates && rm -rf /var/lib/apt/lists/*

# Dépendances d'abord, depuis le lockfile seul : cette couche reste en cache
# tant que uv.lock ne change pas.
COPY pyproject.toml uv.lock .python-version ./
RUN uv sync --locked --no-dev --no-install-project

# Puis le package `oceens` (code, templates, fichiers statiques, données de seed)
COPY src ./src
RUN uv sync --locked --no-dev

# La base n'est pas dans le package : son dossier est fixé ici et monté comme
# volume (voir docker-compose.yaml) pour persister entre les redémarrages.
# Le fichier .env ne doit PAS être copié dans l'image : fournir les secrets via
# --env-file .env au lancement (docker run) ou via les variables d'environnement.
ENV PATH="/app/.venv/bin:$PATH" LOCAL_DATABASE_DIR=/app/database

CMD ["oceens"]
