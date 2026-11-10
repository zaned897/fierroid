-- Limite por cliente de la lista de espera (#74). Ventanas de una hora por
-- cliente; el cliente es un HMAC de su IP, nunca la IP en claro.
CREATE TABLE IF NOT EXISTS waitlist_rate (
  client       TEXT NOT NULL,
  window_start TIMESTAMPTZ NOT NULL,
  hits         INTEGER NOT NULL DEFAULT 0,
  PRIMARY KEY (client, window_start)
);
CREATE INDEX IF NOT EXISTS idx_waitlist_rate_window ON waitlist_rate(window_start);
