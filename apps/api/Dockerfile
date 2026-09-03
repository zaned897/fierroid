# Contexto de build: raiz del repo (docker compose lo hace asi).
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    FIERRO_API_HOST=0.0.0.0 \
    FIERRO_API_PORT=8000

WORKDIR /app

COPY apps/api/pyproject.toml ./apps/api/pyproject.toml
COPY apps/api/src ./apps/api/src

RUN pip install --no-cache-dir "./apps/api[postgres]"

# Sin root: la API no necesita privilegios y en campo corre expuesta a internet.
RUN useradd --system --uid 10001 --create-home fierro
USER fierro

EXPOSE 8000

# python en vez de curl: la imagen slim no trae curl y no vale la pena instalarlo.
HEALTHCHECK --interval=10s --timeout=3s --start-period=15s --retries=6 \
  CMD python -c "import urllib.request as u; u.urlopen('http://127.0.0.1:8000/health', timeout=2)"

CMD ["fierro-api"]
