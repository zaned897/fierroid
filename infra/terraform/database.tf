# Postgres administrado. Aqui vive el dato que el invariante raiz protege una
# vez que salio del corral, asi que las decisiones se inclinan a conservar.

resource "google_sql_database_instance" "principal" {
  name             = "fierro-${var.environment}"
  database_version = "POSTGRES_16"
  region           = var.region

  # En production, `terraform destroy` no debe poder borrar la base con los
  # pesajes de un cliente. Un `-target` mal escrito no puede costar el hato.
  deletion_protection = var.environment == "production"

  settings {
    tier              = var.db_tier
    availability_type = "ZONAL"
    disk_size         = var.db_disk_gb
    disk_type         = "PD_SSD"

    # Crece solo antes de llenarse. Un disco lleno deja de aceptar escrituras,
    # que es exactamente perder lecturas.
    disk_autoresize       = true
    disk_autoresize_limit = var.db_disk_gb * 5

    backup_configuration {
      enabled                        = true
      start_time                     = "08:00" # UTC: madrugada en Mexico
      point_in_time_recovery_enabled = var.environment == "production"
      transaction_log_retention_days = 7

      backup_retention_settings {
        retained_backups = var.environment == "production" ? 30 : 7
        retention_unit   = "COUNT"
      }
    }

    ip_configuration {
      # La IP publica existe pero NO hay redes autorizadas: sin una entrada en
      # authorized_networks, nadie puede abrir una conexion directa. El unico
      # camino es el conector de Cloud SQL, que autentica con IAM y viaja por
      # la red de Google, no por internet abierto.
      #
      # Apagar ipv4 sin configurar una VPC con peering de Service Networking
      # deja la instancia sin ninguna direccion, y entonces el conector
      # tampoco llega. `terraform validate` no lo detecta: falla al aplicar.
      ipv4_enabled = true

      # El proxy cifra igual, pero esto rechaza cualquier intento sin TLS.
      ssl_mode = "ENCRYPTED_ONLY"
    }

    maintenance_window {
      day  = 7 # domingo
      hour = 9 # UTC
    }

    insights_config {
      query_insights_enabled = true
    }
  }
}

resource "google_sql_database" "fierro" {
  name     = "fierro"
  instance = google_sql_database_instance.principal.name
}

# Sin contrasena escrita a mano en ningun lado. Vive en el estado de Terraform
# y en Secret Manager, no en un tfvars que alguien commitea.
resource "random_password" "db" {
  length  = 32
  special = false # el DSN va en una URL; los signos complican el escapado
}

resource "google_sql_user" "app" {
  name     = "fierro"
  instance = google_sql_database_instance.principal.name
  password = random_password.db.result
}

# El DSN completo, para que la API no arme la cadena ni conozca sus partes.
resource "google_secret_manager_secret" "dsn" {
  secret_id = "fierro-${var.environment}-dsn"

  replication {
    auto {}
  }
}

resource "google_secret_manager_secret_version" "dsn" {
  secret = google_secret_manager_secret.dsn.id

  # El host es el socket unix del conector de Cloud SQL, no una direccion IP.
  secret_data = join("", [
    "postgresql://",
    google_sql_user.app.name,
    ":",
    random_password.db.result,
    "@/",
    google_sql_database.fierro.name,
    "?host=/cloudsql/",
    google_sql_database_instance.principal.connection_name,
  ])
}
