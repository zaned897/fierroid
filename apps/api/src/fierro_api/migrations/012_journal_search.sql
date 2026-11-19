-- Busqueda del Diario en espanol (#147). Las reglas de unaccent quedan fijas
-- para el indice. Si cambian, regenerar search_tsv y reconstruir el GIN.
CREATE EXTENSION IF NOT EXISTS unaccent WITH SCHEMA public;

CREATE OR REPLACE FUNCTION public.fierro_unaccent(text) RETURNS text
  LANGUAGE sql IMMUTABLE STRICT PARALLEL SAFE
  AS $$ SELECT public.unaccent('public.unaccent'::regdictionary, $1) $$;

-- El job de derivados (#146) llenara search_text en una etapa posterior.
ALTER TABLE journal_entries
  ADD COLUMN IF NOT EXISTS search_text TEXT NOT NULL DEFAULT '';

ALTER TABLE journal_entries
  ADD COLUMN IF NOT EXISTS search_tsv tsvector
  GENERATED ALWAYS AS (
    to_tsvector('pg_catalog.spanish'::regconfig, public.fierro_unaccent(body || ' ' || search_text))
  ) STORED;

CREATE INDEX IF NOT EXISTS idx_journal_search ON journal_entries USING GIN (search_tsv);
