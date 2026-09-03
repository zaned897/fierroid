-- Timescale queda disponible, pero readings NO se convierte a hypertable todavia.
--
-- Por que: un hypertable exige que todo indice UNIQUE incluya la columna de
-- particion, o sea PRIMARY KEY (event_id, captured_at) en vez de (event_id).
-- Eso degrada la idempotencia: el mismo event_id con otro captured_at entraria
-- dos veces y duplicariamos un pesaje. El invariante raiz manda sobre el
-- rendimiento mientras el piloto sea de 1-3 estaciones.
--
-- Cuando el volumen lo justifique (~decenas de millones de filas), la migracion
-- correcta es agregar una tabla-ledger ingested_events(event_id PK) para la
-- deduplicacion global y recien ahi convertir readings a hypertable.
-- Ver docs/architecture.md y ticket E2-S1.
--
-- La extension es opcional a proposito: Postgres administrado (RDS, Cloud SQL)
-- no siempre la trae. No es un dato de pesaje, asi que degradar aqui es seguro.

DO $$
BEGIN
  EXECUTE 'CREATE EXTENSION IF NOT EXISTS timescaledb';
EXCEPTION WHEN OTHERS THEN
  RAISE NOTICE 'timescaledb no disponible (%); se continua sin la extension', SQLERRM;
END
$$;
