-- Diario de la organización; animal_journal queda como respaldo sin escrituras.
CREATE TABLE IF NOT EXISTS journal_entries (
  entry_id UUID PRIMARY KEY,
  org_id BIGINT NOT NULL REFERENCES organizations(id) ON DELETE RESTRICT,
  author_id BIGINT REFERENCES users(id) ON DELETE RESTRICT,
  occurred_at TIMESTAMPTZ NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  category TEXT NOT NULL CHECK (category IN (
    'observacion', 'alimentacion', 'manejo', 'salud', 'clima', 'insumos', 'equipo', 'general'
  )),
  -- No recortar notas históricas: el límite de 4000 vive en la API.
  body TEXT NOT NULL CHECK (length(btrim(body)) > 0),
  source TEXT NOT NULL DEFAULT 'diario' CHECK (source IN ('diario', 'ficha')),
  CHECK (author_id IS NOT NULL OR source = 'ficha'),
  UNIQUE (entry_id, org_id)
);
CREATE INDEX IF NOT EXISTS idx_journal_entries_history
  ON journal_entries(org_id, occurred_at DESC, entry_id DESC);

CREATE UNIQUE INDEX IF NOT EXISTS uq_animals_id_org ON animals(id, org_id);
CREATE TABLE IF NOT EXISTS journal_entry_animals (
  entry_id UUID NOT NULL,
  animal_id BIGINT NOT NULL,
  org_id BIGINT NOT NULL,
  PRIMARY KEY (entry_id, animal_id),
  FOREIGN KEY (entry_id, org_id)
    REFERENCES journal_entries(entry_id, org_id) ON DELETE CASCADE,
  FOREIGN KEY (animal_id, org_id)
    REFERENCES animals(id, org_id) ON DELETE RESTRICT
);
CREATE INDEX IF NOT EXISTS idx_journal_entry_animals_animal
  ON journal_entry_animals(animal_id, entry_id);

INSERT INTO journal_entries
  (entry_id, org_id, author_id, occurred_at, created_at, category, body)
SELECT j.entry_id, a.org_id, j.author_id, j.occurred_at, j.created_at, j.category, j.body
FROM animal_journal j JOIN animals a ON a.id = j.animal_id
ON CONFLICT (entry_id) DO NOTHING;

INSERT INTO journal_entry_animals(entry_id, animal_id, org_id)
SELECT j.entry_id, j.animal_id, a.org_id
FROM animal_journal j JOIN animals a ON a.id = j.animal_id
ON CONFLICT DO NOTHING;

-- UUID determinista por ficha: ejecutar el SQL de nuevo no duplica las notas.
INSERT INTO journal_entries
  (entry_id, org_id, author_id, occurred_at, created_at, category, body, source)
SELECT md5('animals.notes:' || a.id)::uuid, a.org_id, NULL, a.updated_at, a.updated_at,
       'general', a.notes, 'ficha'
FROM animals a WHERE length(btrim(coalesce(a.notes, ''))) > 0
ON CONFLICT (entry_id) DO NOTHING;

INSERT INTO journal_entry_animals(entry_id, animal_id, org_id)
SELECT md5('animals.notes:' || a.id)::uuid, a.id, a.org_id
FROM animals a WHERE length(btrim(coalesce(a.notes, ''))) > 0
ON CONFLICT DO NOTHING;
