-- Cursor de la copia de la lista de espera en Google Sheets (#129).
-- Una sola fila: el ultimo id de waitlist que ya esta en la hoja.
CREATE TABLE IF NOT EXISTS waitlist_export (
  id         SMALLINT PRIMARY KEY CHECK (id = 1),
  last_id    BIGINT NOT NULL DEFAULT 0,
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
INSERT INTO waitlist_export (id) VALUES (1) ON CONFLICT (id) DO NOTHING;
