-- Multi-cliente: organizacion -> ranchos -> estaciones.
--
-- readings NO lleva org_id ni ranch_id. La pertenencia se deriva por
-- device_id -> devices.ranch_id -> ranches.org_id. Una sola fuente de verdad;
-- denormalizar solo si se mide lento, no por si acaso.

CREATE TABLE IF NOT EXISTS organizations (
  id         BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  slug       TEXT NOT NULL UNIQUE,
  name       TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS ranches (
  id         BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  -- RESTRICT y no CASCADE: borrar una organizacion con ranchos debe doler,
  -- no borrar datos de campo en silencio.
  org_id     BIGINT NOT NULL REFERENCES organizations (id) ON DELETE RESTRICT,
  slug       TEXT NOT NULL,
  name       TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (org_id, slug)
);

CREATE INDEX IF NOT EXISTS idx_ranches_org ON ranches (org_id);

-- ranch_id es NULLABLE a proposito.
--
-- Una estacion nueva puede mandar heartbeat antes de que alguien la asigne a un
-- rancho, y sus lecturas se aceptan igual: el invariante raiz manda. NULL
-- significa "todavia sin asignar", no "invalida". Al asignarla, su historia
-- completa aparece bajo la organizacion correcta.
--
-- ON DELETE SET NULL: borrar un rancho desasigna estaciones, nunca las borra.
ALTER TABLE devices ADD COLUMN IF NOT EXISTS ranch_id BIGINT
  REFERENCES ranches (id) ON DELETE SET NULL;

CREATE INDEX IF NOT EXISTS idx_devices_ranch ON devices (ranch_id);

-- Backfill: las estaciones que ya existian se quedan visibles bajo una
-- organizacion demo en vez de quedar huerfanas.
INSERT INTO organizations (slug, name)
VALUES ('demo', 'Organizacion demo')
ON CONFLICT (slug) DO NOTHING;

INSERT INTO ranches (org_id, slug, name)
SELECT id, 'demo', 'Rancho demo'
FROM organizations
WHERE slug = 'demo'
ON CONFLICT (org_id, slug) DO NOTHING;

UPDATE devices
SET ranch_id = (
  SELECT r.id
  FROM ranches r
  JOIN organizations o ON o.id = r.org_id
  WHERE o.slug = 'demo' AND r.slug = 'demo'
)
WHERE ranch_id IS NULL;
