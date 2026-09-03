-- Credenciales de sesion: API keys revocables en vez de JWT.
--
-- Por que el cambio: un JWT no se puede revocar antes de que expire. Una API
-- key vive como hash en esta tabla, asi que cerrar una sesion es borrar una
-- fila. Es tambien lo que permite "cerrar sesion en todos los dispositivos".

CREATE TABLE IF NOT EXISTS api_keys (
  id           BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  user_id      BIGINT NOT NULL REFERENCES users (id) ON DELETE CASCADE,

  -- SHA-256, no argon2. La llave es aleatoria de 256 bits, asi que no hay
  -- nada que un hash lento proteja: no se puede adivinar por diccionario.
  -- Y se verifica en CADA request; argon2 costaria ~80 ms por llamada.
  key_hash     TEXT NOT NULL UNIQUE,

  -- Primeros caracteres en claro, solo para que el usuario reconozca cual es
  -- cual en la lista. No sirve para autenticar.
  key_prefix   TEXT NOT NULL,

  name         TEXT,
  created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
  last_used_at TIMESTAMPTZ,
  expires_at   TIMESTAMPTZ,
  revoked_at   TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_api_keys_user ON api_keys (user_id);

-- La contrasena deja de ser obligatoria: el camino normal es Google, y un
-- usuario que solo entra por Google no tiene ninguna.
ALTER TABLE users ALTER COLUMN password_hash DROP NOT NULL;

-- Proveedor de identidad, para saber como entro cada quien.
ALTER TABLE users ADD COLUMN IF NOT EXISTS google_sub TEXT;
CREATE UNIQUE INDEX IF NOT EXISTS idx_users_google_sub ON users (google_sub)
  WHERE google_sub IS NOT NULL;
