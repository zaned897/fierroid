-- Esquema base de la API en Postgres.
-- Espeja el esquema SQLite de store.py para que el contrato de datos no cambie.

CREATE TABLE IF NOT EXISTS readings (
  event_id    TEXT PRIMARY KEY,
  device_id   TEXT NOT NULL,
  tag_id      TEXT NOT NULL,
  weight_kg   DOUBLE PRECISION NOT NULL,
  captured_at TIMESTAMPTZ NOT NULL,
  stable      BOOLEAN NOT NULL,
  source      TEXT NOT NULL,
  received_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Listado reciente (GET /v1/readings ordena por captured_at DESC).
CREATE INDEX IF NOT EXISTS idx_readings_captured ON readings (captured_at DESC);

-- Historial por animal: la consulta que pide la PWA al abrir un arete.
CREATE INDEX IF NOT EXISTS idx_readings_tag_captured ON readings (tag_id, captured_at DESC);

-- Diagnostico por estacion.
CREATE INDEX IF NOT EXISTS idx_readings_device_captured ON readings (device_id, captured_at DESC);

CREATE TABLE IF NOT EXISTS devices (
  device_id     TEXT PRIMARY KEY,
  pending_count INTEGER NOT NULL DEFAULT 0,
  agent_version TEXT,
  uptime_s      BIGINT,
  last_seen     TIMESTAMPTZ NOT NULL DEFAULT now()
);
