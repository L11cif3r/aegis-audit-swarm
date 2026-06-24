# backend/Dockerfile — Talamanda Trust Node (gateway)
FROM python:3.14-slim AS base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# System deps for asyncpg/psycopg2/cryptography wheels.
RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential libpq-dev curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

COPY . .

# Run as non-root (sovereign hardening).
RUN useradd --create-home --uid 10001 trustnode \
    && chown -R trustnode:trustnode /app
USER trustnode

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD curl -fsS http://127.0.0.1:${PORT:-8000}/health || exit 1

# Apply migrations (fail-hard so we never serve against an unmigrated schema),
# then serve. Binds $PORT (Render/Heroku) with an 8000 fallback (compose/local).
# Workers scale via UVICORN_WORKERS.
CMD ["sh", "-c", "alembic upgrade head && uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000} --workers ${UVICORN_WORKERS:-2} --proxy-headers --forwarded-allow-ips '*'"]
