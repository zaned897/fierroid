-- Usuarios. Un usuario pertenece a UNA organizacion.
--
-- El superusuario es la excepcion: no tiene organizacion porque las ve todas.
-- El CHECK lo vuelve imposible de configurar mal: un usuario normal sin
-- organizacion no veria nada, o peor, lo veria todo.

CREATE TABLE IF NOT EXISTS users (
  id            BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  email         TEXT NOT NULL,
  password_hash TEXT NOT NULL,
  full_name     TEXT,
  org_id        BIGINT REFERENCES organizations (id) ON DELETE RESTRICT,
  is_superuser  BOOLEAN NOT NULL DEFAULT false,
  is_active     BOOLEAN NOT NULL DEFAULT true,
  created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
  last_login_at TIMESTAMPTZ,
  CONSTRAINT users_org_requerida CHECK (is_superuser OR org_id IS NOT NULL)
);

-- Unico sobre lower(email): "Ana@rancho.mx" y "ana@rancho.mx" son la misma
-- persona, y permitir ambos es una via de suplantacion.
CREATE UNIQUE INDEX IF NOT EXISTS idx_users_email ON users (lower(email));

CREATE INDEX IF NOT EXISTS idx_users_org ON users (org_id);
