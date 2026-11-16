-- Diario del rancho (#149): entradas por organizacion con 0..n animales.
--
-- `animal_journal` (007) ataba cada nota a UN animal. Aqui la entrada es de la
-- organizacion y los animales van en una tabla puente. Las notas existentes se
-- copian con el mismo `entry_id`, autor y fechas; `animal_journal` queda
-- congelada (sin escrituras nuevas) y se borra en un ticket aparte.
--
-- Todo el archivo es idempotente: si corre dos veces no duplica nada.

-- Permite que la tabla puente exija que el animal sea de la misma organizacion
-- que la entrada (llave foranea compuesta). `id` ya es unico; esto solo agrega
-- el par.
CREATE UNIQUE INDEX IF NOT EXISTS uq_animals_id_org ON animals (id, org_id);

CREATE TABLE IF NOT EXISTS journal_entries (
  entry_id    UUID PRIMARY KEY,
  org_id      BIGINT NOT NULL REFERENCES organizations (id) ON DELETE RESTRICT,
  -- NULL solo en entradas migradas de `animals.notes`, que no tenian autor.
  author_id   BIGINT REFERENCES users (id) ON DELETE RESTRICT,
  occurred_at TIMESTAMPTZ NOT NULL,
  created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
  category    TEXT NOT NULL CHECK (category IN (
    'observacion', 'alimentacion', 'manejo', 'salud',
    'clima', 'insumos', 'equipo', 'general'
  )),
  -- El tope de 4000 lo pone la API. Aqui solo "no vacio": una nota vieja de la
  -- ficha mas larga no se recorta al migrar.
  body        TEXT NOT NULL CHECK (length(btrim(body)) > 0),
  -- De donde salio la entrada: 'diario' (API) o 'ficha' (campo Notas).
  source      TEXT NOT NULL DEFAULT 'diario' CHECK (source IN ('diario', 'ficha')),
  UNIQUE (entry_id, org_id)
);

CREATE INDEX IF NOT EXISTS idx_journal_entries_org_time
  ON journal_entries (org_id, occurred_at DESC, entry_id DESC);

CREATE TABLE IF NOT EXISTS journal_entry_animals (
  entry_id  UUID NOT NULL,
  animal_id BIGINT NOT NULL,
  org_id    BIGINT NOT NULL,
  PRIMARY KEY (entry_id, animal_id),
  FOREIGN KEY (entry_id, org_id) REFERENCES journal_entries (entry_id, org_id) ON DELETE CASCADE,
  FOREIGN KEY (animal_id, org_id) REFERENCES animals (id, org_id) ON DELETE RESTRICT
);

CREATE INDEX IF NOT EXISTS idx_journal_entry_animals_animal
  ON journal_entry_animals (animal_id, entry_id);

-- 1. Bitacora por animal -> diario, mismo entry_id, autor y fechas.
INSERT INTO journal_entries (entry_id, org_id, author_id, occurred_at, created_at, category, body, source)
SELECT j.entry_id, a.org_id, j.author_id, j.occurred_at, j.created_at, j.category, j.body, 'diario'
FROM animal_journal j
JOIN animals a ON a.id = j.animal_id
ON CONFLICT (entry_id) DO NOTHING;

INSERT INTO journal_entry_animals (entry_id, animal_id, org_id)
SELECT j.entry_id, j.animal_id, a.org_id
FROM animal_journal j
JOIN animals a ON a.id = j.animal_id
ON CONFLICT (entry_id, animal_id) DO NOTHING;

-- 2. Campo libre `animals.notes` -> una entrada 'general' por ficha.
--    El entry_id se deriva del id del animal, asi una segunda corrida cae en
--    el mismo id y no duplica. La columna no se borra en este issue.
INSERT INTO journal_entries (entry_id, org_id, author_id, occurred_at, created_at, category, body, source)
SELECT md5('animals.notes:' || a.id)::uuid, a.org_id, NULL, a.updated_at, a.updated_at,
       'general', a.notes, 'ficha'
FROM animals a
WHERE a.notes IS NOT NULL AND length(btrim(a.notes)) > 0
ON CONFLICT (entry_id) DO NOTHING;

INSERT INTO journal_entry_animals (entry_id, animal_id, org_id)
SELECT md5('animals.notes:' || a.id)::uuid, a.id, a.org_id
FROM animals a
WHERE a.notes IS NOT NULL AND length(btrim(a.notes)) > 0
ON CONFLICT (entry_id, animal_id) DO NOTHING;
