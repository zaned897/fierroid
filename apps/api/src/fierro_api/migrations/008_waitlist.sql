CREATE TABLE IF NOT EXISTS waitlist (
  id BIGSERIAL PRIMARY KEY,
  name TEXT NOT NULL CHECK (length(name) BETWEEN 1 AND 100),
  email TEXT NOT NULL UNIQUE CHECK (length(email) <= 254),
  stations INTEGER NOT NULL CHECK (stations BETWEEN 1 AND 1000),
  consent_version TEXT NOT NULL DEFAULT 'contact-v1',
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_waitlist_created ON waitlist(created_at);
