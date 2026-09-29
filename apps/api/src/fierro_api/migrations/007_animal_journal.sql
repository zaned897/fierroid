-- Bitácora append-only. La clave del cliente permite reintentar sin duplicar.
CREATE TABLE IF NOT EXISTS animal_journal (
  entry_id UUID PRIMARY KEY,
  animal_id BIGINT NOT NULL REFERENCES animals(id) ON DELETE RESTRICT,
  author_id BIGINT NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
  occurred_at TIMESTAMPTZ NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  category TEXT NOT NULL CHECK (category IN ('observacion', 'alimentacion', 'manejo', 'salud')),
  body TEXT NOT NULL CHECK (length(btrim(body)) BETWEEN 1 AND 4000)
);
CREATE INDEX IF NOT EXISTS idx_animal_journal_history
  ON animal_journal(animal_id, occurred_at DESC, entry_id DESC);
