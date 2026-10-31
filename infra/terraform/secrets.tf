# La base ya no vive aqui: es Neon, fuera de Google Cloud.
#
# Neon tiene nivel gratuito y escala a cero, que es donde estaba casi todo el
# costo de este despliegue. Lo que queda en Google es el contenedor de la API,
# que a este trafico cae dentro del nivel gratuito de Cloud Run.
#
# Terraform no crea la base: solo guarda las cadenas de conexion como secretos.
# Crear el proyecto de Neon es un paso manual de una sola vez.

# --- DSN de la aplicacion (con pooler) --------------------------------------

resource "google_secret_manager_secret" "dsn" {
  secret_id = "fierro-${var.environment}-dsn"

  replication {
    auto {}
  }
}

resource "google_secret_manager_secret_version" "dsn" {
  secret      = google_secret_manager_secret.dsn.id
  secret_data = var.db_dsn
}

# --- DSN directo, solo para migraciones -------------------------------------
#
# El pooler de Neon es transaccional (PgBouncer en modo transaction), y ahi el
# estado de sesion no sobrevive entre sentencias. `fierro-api-migrate` toma un
# `pg_advisory_lock`, que es de SESION: por el pooler se tomaria y se soltaria
# en conexiones distintas, y dos migraciones simultaneas correrian a la vez sin
# que nada las detenga.
#
# Por eso las migraciones usan la cadena directa, sin `-pooler` en el host.

resource "google_secret_manager_secret" "dsn_directo" {
  secret_id = "fierro-${var.environment}-dsn-directo"

  replication {
    auto {}
  }
}

resource "google_secret_manager_secret_version" "dsn_directo" {
  secret      = google_secret_manager_secret.dsn_directo.id
  secret_data = var.db_dsn_direct
}

# --- Clave de Anthropic, para el asistente (#110) ----------------------------
#
# Opcional: sin ella el asistente responde 503 y la PWA lo dice, nunca inventa.
# El secreto solo existe si el .tfvars trae la clave. Ponerla a mano con
# `gcloud run services update` no sirve: el siguiente apply la quitaria.

resource "google_secret_manager_secret" "anthropic" {
  count     = var.anthropic_api_key == "" ? 0 : 1
  secret_id = "fierro-${var.environment}-anthropic-api-key"

  replication {
    auto {}
  }
}

resource "google_secret_manager_secret_version" "anthropic" {
  count       = var.anthropic_api_key == "" ? 0 : 1
  secret      = google_secret_manager_secret.anthropic[0].id
  secret_data = var.anthropic_api_key
}
