-- Dinero, etapa 1 (#173). 012 reservado a busqueda, 013 a adjuntos.
-- Ledger append-only: la aplicacion solo SELECT/INSERT, nunca UPDATE/DELETE.
-- Una correccion es una anulacion + un movimiento nuevo; no hay importes negativos.
-- Para roles SQL distintos del propietario, conceder solo SELECT e INSERT en
-- estas tablas y SELECT en la vista; no conceder UPDATE, DELETE ni TRUNCATE.
CREATE TABLE IF NOT EXISTS money_movements (
  movement_id UUID PRIMARY KEY,
  org_id BIGINT NOT NULL REFERENCES organizations(id) ON DELETE RESTRICT,
  kind TEXT NOT NULL CHECK (kind IN ('compra','venta','gasto','precio_mercado')),
  category TEXT CHECK (category IN (
    'alimento','sanidad','mano_obra','instalaciones','transporte','otros'
  )),
  amount_mxn NUMERIC(12,2) CHECK (amount_mxn > 0),
  precio_kg_mxn NUMERIC(10,2) CHECK (precio_kg_mxn > 0),
  weight_kg NUMERIC(8,2) CHECK (weight_kg > 0),
  occurred_on DATE NOT NULL,
  period_start DATE,
  period_end DATE,
  scope TEXT NOT NULL CHECK (scope IN ('animales','corral','hato')),
  corral TEXT CHECK (length(btrim(corral)) BETWEEN 1 AND 120),
  source_entry_id UUID,
  status TEXT NOT NULL DEFAULT 'confirmado'
    CHECK (status IN ('propuesto','confirmado','anulado')),
  voids_movement_id UUID UNIQUE,
  author_id BIGINT NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (movement_id, org_id),
  FOREIGN KEY (source_entry_id, org_id)
    REFERENCES journal_entries(entry_id, org_id) ON DELETE RESTRICT,
  FOREIGN KEY (voids_movement_id, org_id)
    REFERENCES money_movements(movement_id, org_id) ON DELETE RESTRICT,
  CHECK (voids_movement_id IS NULL OR voids_movement_id <> movement_id),
  CHECK ((kind='gasto' AND category IS NOT NULL) OR (kind<>'gasto' AND category IS NULL)),
  CHECK ((kind='precio_mercado' AND precio_kg_mxn IS NOT NULL AND amount_mxn IS NULL)
    OR (kind<>'precio_mercado' AND amount_mxn IS NOT NULL AND precio_kg_mxn IS NULL)),
  CHECK (weight_kg IS NULL OR kind IN ('compra','venta')),
  CHECK (kind NOT IN ('compra','venta') OR scope='animales'),
  CHECK (kind<>'precio_mercado' OR scope='hato'),
  CHECK ((scope='corral' AND corral IS NOT NULL) OR (scope<>'corral' AND corral IS NULL)),
  CHECK ((period_start IS NULL AND period_end IS NULL) OR
    (kind='gasto' AND period_start IS NOT NULL AND period_end IS NOT NULL
      AND period_end >= period_start))
);

CREATE TABLE IF NOT EXISTS money_movement_animals (
  movement_id UUID NOT NULL,
  animal_id BIGINT NOT NULL,
  org_id BIGINT NOT NULL,
  PRIMARY KEY (movement_id, animal_id),
  FOREIGN KEY (movement_id, org_id)
    REFERENCES money_movements(movement_id, org_id) ON DELETE CASCADE,
  FOREIGN KEY (animal_id, org_id)
    REFERENCES animals(id, org_id) ON DELETE RESTRICT
);
CREATE INDEX IF NOT EXISTS idx_money_org_date
  ON money_movements(org_id, occurred_on DESC, created_at DESC, movement_id DESC);
CREATE INDEX IF NOT EXISTS idx_money_animals ON money_movement_animals(animal_id, movement_id);

-- La cardinalidad necesita ver la transaccion completa (fila + asociaciones).
CREATE OR REPLACE FUNCTION check_money_animals() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE
  movement UUID;
  row_kind TEXT;
  row_scope TEXT;
  total INTEGER;
BEGIN
  movement := COALESCE(NEW.movement_id, OLD.movement_id);
  SELECT kind, scope INTO row_kind, row_scope FROM money_movements WHERE movement_id=movement;
  IF NOT FOUND THEN RETURN NULL; END IF;
  SELECT count(*) INTO total FROM money_movement_animals WHERE movement_id=movement;
  IF (row_kind IN ('compra','venta') AND total<>1)
    OR (row_scope='animales' AND total=0)
    OR (row_scope<>'animales' AND total<>0) THEN
    RAISE EXCEPTION 'Animales incompatibles con el movimiento' USING ERRCODE='23514';
  END IF;
  RETURN NULL;
END $$;
DROP TRIGGER IF EXISTS money_animals_valid ON money_movements;
CREATE CONSTRAINT TRIGGER money_animals_valid AFTER INSERT OR UPDATE ON money_movements
  DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION check_money_animals();
DROP TRIGGER IF EXISTS money_links_valid ON money_movement_animals;
CREATE CONSTRAINT TRIGGER money_links_valid AFTER INSERT OR UPDATE OR DELETE
  ON money_movement_animals DEFERRABLE INITIALLY DEFERRED
  FOR EACH ROW EXECUTE FUNCTION check_money_animals();

CREATE OR REPLACE VIEW money_movements_ledger AS
SELECT m.*, CASE
  WHEN m.voids_movement_id IS NOT NULL THEN 'anulacion'
  WHEN EXISTS (SELECT 1 FROM money_movements v
    WHERE v.voids_movement_id=m.movement_id AND v.org_id=m.org_id AND v.status='confirmado')
    THEN 'anulado'
  ELSE m.status END AS estado
FROM money_movements m;
