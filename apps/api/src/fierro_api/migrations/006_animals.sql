-- Ficha del animal: alias, notas y foto.
--
-- La foto va en tabla APARTE, no en una columna de animals. Dos razones:
--
-- 1. Consultar la lista de animales nunca toca el binario, ni por accidente
--    con un SELECT *.
-- 2. El dia que las fotos se muevan a almacenamiento de objetos, la migracion
--    es una tabla entera y un modulo, no una columna entrelazada con el resto.
--    Ver los issues abiertos sobre ese cambio.

CREATE TABLE IF NOT EXISTS animals (
  id         BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  org_id     BIGINT NOT NULL REFERENCES organizations (id) ON DELETE RESTRICT,

  -- El arete es unico por organizacion, no globalmente: si un animal se vende,
  -- el comprador lleva su propia ficha sin ver la del vendedor.
  tag_id     TEXT NOT NULL,

  alias      TEXT,
  notes      TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),

  UNIQUE (org_id, tag_id)
);

CREATE INDEX IF NOT EXISTS idx_animals_org ON animals (org_id);

CREATE TABLE IF NOT EXISTS animal_photos (
  animal_id    BIGINT PRIMARY KEY REFERENCES animals (id) ON DELETE CASCADE,
  bytes        BYTEA NOT NULL,
  content_type TEXT NOT NULL,
  byte_size    INTEGER NOT NULL,
  updated_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);
