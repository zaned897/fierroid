-- El numero 012 esta reservado para la busqueda del Diario (#147).
CREATE TABLE IF NOT EXISTS journal_attachments (
  attachment_id UUID PRIMARY KEY,
  entry_id UUID NOT NULL,
  org_id BIGINT NOT NULL,
  kind TEXT NOT NULL CHECK (kind IN ('photo', 'audio')),
  content_type TEXT NOT NULL CHECK (content_type IN
    ('image/jpeg', 'image/webp', 'audio/webm', 'audio/mp4')),
  byte_size INTEGER NOT NULL CHECK (byte_size BETWEEN 1 AND 2097152),
  duration_ms INTEGER CHECK (duration_ms BETWEEN 1 AND 120000),
  sha256 BYTEA NOT NULL CHECK (octet_length(sha256) = 32),
  storage_key TEXT NOT NULL UNIQUE,
  storage_generation TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  FOREIGN KEY (entry_id, org_id) REFERENCES journal_entries(entry_id, org_id) ON DELETE RESTRICT,
  CHECK ((kind = 'audio') = (duration_ms IS NOT NULL)),
  CHECK ((kind = 'photo') = (content_type IN ('image/jpeg', 'image/webp')))
);
CREATE INDEX IF NOT EXISTS idx_journal_attachments_entry
  ON journal_attachments(org_id, entry_id, created_at, attachment_id);
