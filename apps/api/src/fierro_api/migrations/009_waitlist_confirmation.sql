ALTER TABLE waitlist
  ADD COLUMN IF NOT EXISTS confirmation_token_hash TEXT,
  ADD COLUMN IF NOT EXISTS confirmation_sent_at TIMESTAMPTZ,
  ADD COLUMN IF NOT EXISTS confirmed_at TIMESTAMPTZ;

CREATE UNIQUE INDEX IF NOT EXISTS idx_waitlist_confirmation_token_hash
  ON waitlist(confirmation_token_hash)
  WHERE confirmation_token_hash IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_waitlist_confirmed_at
  ON waitlist(confirmed_at);
