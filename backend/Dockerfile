# ── Stage 1: Abhängigkeiten bauen ─────────────────────────────────────────────
FROM python:3.12-slim AS deps

WORKDIR /build

# System-Pakete für asyncpg (C-Compiler nötig)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt


# ── Stage 2: Produktions-Image ────────────────────────────────────────────────
FROM python:3.12-slim AS prod

WORKDIR /app

# Nur Runtime-Libs (kein gcc)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Abhängigkeiten aus dem Build-Stage übernehmen
COPY --from=deps /install /usr/local

# Quellcode kopieren
COPY . .

# Nicht-root User für Sicherheit
RUN adduser --system --no-create-home --group appuser \
    && chown -R appuser:appuser /app
USER appuser

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]


# ── Stage 3: Dev-Image (Hot-Reload) ───────────────────────────────────────────
FROM prod AS dev

USER root
RUN pip install --no-cache-dir watchfiles
USER appuser

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
