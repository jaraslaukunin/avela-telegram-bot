# Avela backend: FastAPI (API + Telegram webhook) и worker — один образ,
# разные команды запуска (см. docker-compose.prod.yml).
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
# Миграции внутри образа: их можно применять из контейнера (python -m app.cli / db push)
COPY supabase ./supabase

RUN useradd --create-home --uid 1001 avela \
    && chown -R avela:avela /app
USER avela

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD curl -fsS http://127.0.0.1:8000/health || exit 1

CMD ["python", "-m", "app.main"]
