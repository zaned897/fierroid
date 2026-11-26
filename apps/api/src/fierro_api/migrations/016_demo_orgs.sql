-- Rancho demo por cuenta.
--
-- Los datos de demostracion viven en una organizacion APARTE, nunca mezclados
-- con los de la cuenta real. Por que no una marca "sintetico" en cada fila:
-- el libro de dinero (014) es de solo agregar, y los repartos de gasto de
-- corral y hato abarcan todos los animales de la organizacion. Mezclar exigiria
-- un filtro en cada consulta y borrar del libro para purgar; un filtro olvidado
-- da cifras falsas revueltas con las reales. Separar por organizacion aisla por
-- construccion: los pesajes ya se separan por estacion, y lo demas por org_id.
--
-- es_demo: la organizacion solo contiene datos de demostracion. La web lo
-- anuncia siempre con un aviso fijo, y es la unica que el comando de purga
-- acepta borrar.
-- demo_de_org_id: la cuenta real cuyo rancho demo es. UNIQUE: una por cuenta.
-- Un usuario de esa cuenta puede leer y escribir aqui con ?org=<slug>.
ALTER TABLE organizations ADD COLUMN IF NOT EXISTS es_demo BOOLEAN NOT NULL DEFAULT false;
ALTER TABLE organizations ADD COLUMN IF NOT EXISTS demo_de_org_id BIGINT UNIQUE
  REFERENCES organizations (id) ON DELETE RESTRICT;

DO $$
BEGIN
  ALTER TABLE organizations ADD CONSTRAINT organizations_demo_de_requiere_demo
    CHECK (demo_de_org_id IS NULL OR (es_demo AND demo_de_org_id <> id));
EXCEPTION WHEN duplicate_object THEN NULL;
END
$$;
