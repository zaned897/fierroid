ALTER TABLE waitlist
  ADD COLUMN IF NOT EXISTS state TEXT NOT NULL DEFAULT 'No especificado'
  CHECK (length(state) BETWEEN 1 AND 80);
