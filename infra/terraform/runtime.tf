# Registro de imagenes, identidad y el servicio de Cloud Run.

# El registro es uno para el proyecto, no uno por entorno, y esta config se
# aplica una vez por entorno. Sin el count, el segundo workspace intenta crear
# un repositorio que ya existe y falla; e importarlo seria peor, porque un
# `destroy` en stage se llevaria las imagenes desde las que corre production.
#
# Compartirlo y no partirlo en dos es a proposito: `docs/environments.md` dice
# que nada entra a production sin pasar por stage, y eso solo se puede cumplir
# de verdad promoviendo el mismo digest que stage validó. Con un registro por
# entorno habria que reconstruir, y reconstruir es otra imagen.
resource "google_artifact_registry_repository" "images" {
  count = var.crea_registro ? 1 : 0

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

# Agregar count reindexa la direccion del recurso. Sin esto, el estado de
# production sigue apuntando a `.images` mientras la config declara `.images[0]`,
# y el plan sale con un destroy del registro con las imagenes dentro.
moved {
  from = google_artifact_registry_repository.images
  to   = google_artifact_registry_repository.images[0]
}

data "google_artifact_registry_repository" "images" {
  count = var.crea_registro ? 0 : 1

  location      = var.region
  repository_id = "fierro"
}

locals {
  registro_id = one(
    concat(
      google_artifact_registry_repository.images[*].repository_id,
      data.google_artifact_registry_repository.images[*].repository_id,
    )
  )
}

# Identidad propia del servicio. Sin esto usaria la cuenta por defecto de
# Compute, que trae permisos de editor sobre todo el proyecto.
resource "google_service_account" "api" {
  account_id   = "fierro-api-${var.environment}"
  display_name = "Fierro API (${var.environment})"
}

# Acceso al secreto concreto, no a todos los del proyecto.
resource "google_secret_manager_secret_iam_member" "api_dsn" {
  secret_id = google_secret_manager_secret.dsn.id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.api.email}"
}

# El job de migraciones lee la cadena directa, que es otro secreto.
resource "google_secret_manager_secret_iam_member" "migrate_dsn" {
  secret_id = google_secret_manager_secret.dsn_directo.id
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

      containers {
        image   = var.api_image
        command = ["fierro-api-migrate"]

        # La directa, no la del pooler: el advisory lock es de sesion.
        env {
          name = "FIERRO_API_DSN"
          value_source {
            secret_key_ref {
              secret  = google_secret_manager_secret.dsn_directo.secret_id
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

      }
    }
  }

  depends_on = [
    google_secret_manager_secret_version.dsn_directo,
    google_secret_manager_secret_iam_member.migrate_dsn,
  ]
}
