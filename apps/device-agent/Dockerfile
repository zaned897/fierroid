# Agent en contenedor SOLO para demo y pruebas de integracion con hardware mock.
# En la Raspberry Pi real corre como servicio systemd, no en Docker:
# el acceso a /dev/ttyUSB* y el watchdog piden el host.
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    FIERRO_MOCK_HW=1

WORKDIR /app

COPY apps/device-agent/pyproject.toml ./apps/device-agent/pyproject.toml
COPY apps/device-agent/README.md ./apps/device-agent/README.md
COPY apps/device-agent/src ./apps/device-agent/src

RUN pip install --no-cache-dir ./apps/device-agent

RUN useradd --system --uid 10002 --create-home fierro \
    && mkdir -p /data && chown fierro:fierro /data
USER fierro

VOLUME ["/data"]

CMD ["fierro-device"]
