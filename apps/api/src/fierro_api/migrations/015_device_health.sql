-- Salud de la estacion en el heartbeat (#184).
--
-- Todas nullable: NULL = la estacion no lo reporta (agente viejo, o no aplica
-- en esa plataforma). Nunca 0 por defecto, que se confundiria con una lectura real.
-- Numero 015: 012-014 los tienen PRs abiertos.
ALTER TABLE devices ADD COLUMN IF NOT EXISTS disk_used_pct   DOUBLE PRECISION;
ALTER TABLE devices ADD COLUMN IF NOT EXISTS cpu_temp_c      DOUBLE PRECISION;
-- Mascara de `vcgencmd get_throttled` (bits de subvoltaje y limite termico).
ALTER TABLE devices ADD COLUMN IF NOT EXISTS throttled       BIGINT;
ALTER TABLE devices ADD COLUMN IF NOT EXISTS clock_synced    BOOLEAN;
ALTER TABLE devices ADD COLUMN IF NOT EXISTS hw_rev          TEXT;
ALTER TABLE devices ADD COLUMN IF NOT EXISTS last_sync_ok_at TIMESTAMPTZ;
ALTER TABLE devices ADD COLUMN IF NOT EXISTS last_error      TEXT;
