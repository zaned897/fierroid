# Registro de imagenes, identidad y el servicio de Cloud Run.

resource "google_artifact_registry_repository" "images" {
  location      = var.region
  repository_id = "fierro"
  format        = "DOCKER"
  description   = "Imagenes de la API y del agent. Cloud Run solo despliega desde aqui."

  cleanup_policies {
    id     = "conservar-recientes"
    action = "KEEP"
    most_recent_versions {
      keep_count = 20
    }
  }
}

# Identidad propia del servicio. Sin esto usaria la cuenta por defecto de
# Compute, que trae permisos de editor sobre todo el proyecto.
resource "google_service_account" "api" {
  account_id   = "fierro-api-${var.environment}"
  display_name = "Fierro API (${var.environment})"
}

resource "google_project_iam_member" "api_cloudsql" {
  project = var.project_id
  role    = "roles/cloudsql.client"
  member  = "serviceAccount:${google_service_account.api.email}"
}

# Acceso al secreto concreto, no a todos los del proyecto.
resource "google_secret_manager_secret_iam_member" "api_dsn" {
  secret_id = google_secret_manager_secret.dsn.id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.api.email}"
}

locals {
  # Configuracion compartida entre el servicio y el job de migraciones: si se
  # separan, la migracion corre contra una base y la API contra otra.
  env_comun = {
    FIERRO_ENV              = var.environment
    FIERRO_API_CORS_ORIGINS = var.cors_origins
    FIERRO_GOOGLE_CLIENT_ID = var.google_client_id
    FIERRO_API_KEY_TTL_DAYS = tostring(var.api_key_ttl_days)
  }
}

resource "google_cloud_run_v2_service" "api" {
  name     = "fierro-api-${var.environment}"
  location = var.region

  # La API es publica a proposito: la autenticacion es nuestra, no de Google.
  # Las estaciones tampoco tienen identidad de Google con que firmar.
  ingress = "INGRESS_TRAFFIC_ALL"

  template {
    service_account = google_service_account.api.email

    scaling {
      min_instance_count = var.min_instances
      max_instance_count = var.max_instances
    }

    volumes {
      name = "cloudsql"
      cloud_sql_instance {
        instances = [google_sql_database_instance.principal.connection_name]
      }
    }

    containers {
      image = var.api_image

      ports {
        container_port = 8000
      }

      resources {
        limits = {
          cpu    = "1"
          memory = "512Mi"
        }
        # CPU solo mientras atiende: es lo que hace que escalar a cero sirva.
        cpu_idle = true
      }

      dynamic "env" {
        for_each = local.env_comun
        content {
          name  = env.key
          value = env.value
        }
      }

      env {
        name = "FIERRO_API_DSN"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.dsn.secret_id
            version = "latest"
          }
        }
      }

      volume_mounts {
        name       = "cloudsql"
        mount_path = "/cloudsql"
      }

      startup_probe {
        http_get {
          path = "/health"
        }
        initial_delay_seconds = 5
        period_seconds        = 5
        failure_threshold     = 6
      }

      liveness_probe {
        http_get {
          path = "/health"
        }
        period_seconds = 30
      }
    }
  }

  depends_on = [
    google_secret_manager_secret_version.dsn,
    google_secret_manager_secret_iam_member.api_dsn,
  ]
}

# La API se autentica sola; Cloud Run no debe pedir credencial de Google encima.
resource "google_cloud_run_v2_service_iam_member" "publico" {
  name     = google_cloud_run_v2_service.api.name
  location = google_cloud_run_v2_service.api.location
  role     = "roles/run.invoker"
  member   = "allUsers"
}

# Migraciones como job aparte, no al arrancar el contenedor: con varias
# instancias, todas correrian las migraciones a la vez. El job corre una sola
# vez y de todas formas fierro-api-migrate toma un advisory lock.
#
#   gcloud run jobs execute fierro-migrate-<entorno> --region <region> --wait
resource "google_cloud_run_v2_job" "migrate" {
  name     = "fierro-migrate-${var.environment}"
  location = var.region

  template {
    template {
      service_account = google_service_account.api.email
      max_retries     = 1

      volumes {
        name = "cloudsql"
        cloud_sql_instance {
          instances = [google_sql_database_instance.principal.connection_name]
        }
      }

      containers {
        image   = var.api_image
        command = ["fierro-api-migrate"]

        env {
          name = "FIERRO_API_DSN"
          value_source {
            secret_key_ref {
              secret  = google_secret_manager_secret.dsn.secret_id
              version = "latest"
            }
          }
        }

        # El validador exige estas dos incluso para migrar.
        env {
          name  = "FIERRO_ENV"
          value = var.environment
        }

        env {
          name  = "FIERRO_API_CORS_ORIGINS"
          value = var.cors_origins
        }

        volume_mounts {
          name       = "cloudsql"
          mount_path = "/cloudsql"
        }
      }
    }
  }

  depends_on = [
    google_secret_manager_secret_version.dsn,
    google_secret_manager_secret_iam_member.api_dsn,
  ]
}
