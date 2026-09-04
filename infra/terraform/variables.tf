variable "project_id" {
  description = "ID del proyecto de Google Cloud."
  type        = string
}

variable "environment" {
  description = "stage o production. Define nombres, tamanos y protecciones."
  type        = string

  validation {
    condition     = contains(["stage", "production"], var.environment)
    error_message = "environment debe ser 'stage' o 'production'. Un typo aqui crea un entorno paralelo silencioso."
  }
}

variable "region" {
  description = <<-EOT
    Region de Google Cloud.

    northamerica-south1 es Queretaro: el salto de latencia importa cuando la
    PWA se usa desde un celular en el corral, no en una oficina.
  EOT
  type        = string
  default     = "northamerica-south1"
}

variable "api_image" {
  description = <<-EOT
    Imagen completa de la API, con etiqueta o digest.

    Cloud Run solo despliega desde Artifact Registry, no desde GHCR. El
    workflow de publicacion sube la imagen aqui ademas de a GHCR.

    Usar el digest (sha256:...) y no una etiqueta movil en production: una
    etiqueta se reescribe y deja de saberse que esta corriendo.
  EOT
  type        = string
}

variable "db_dsn" {
  description = <<-EOT
    Cadena de conexion de Neon CON pooler, para la API.

    La da Neon en su panel: es la que lleva `-pooler` en el host.

    Nunca se escribe en un archivo commiteado. Va en un .tfvars local, que
    esta en .gitignore, y de ahi a Secret Manager.
  EOT
  type        = string
  sensitive   = true
}

variable "db_dsn_direct" {
  description = <<-EOT
    Cadena de conexion de Neon SIN pooler, solo para migraciones.

    `fierro-api-migrate` toma un advisory lock, que es de sesion. El pooler de
    Neon es transaccional y no conserva estado de sesion entre sentencias, asi
    que por ahi el lock no protegeria nada.
  EOT
  type        = string
  sensitive   = true
}

variable "cors_origins" {
  description = <<-EOT
    Origenes permitidos para la PWA, separados por coma.

    La API se niega a arrancar si esto queda en '*' fuera de dev, asi que un
    valor vacio aqui rompe el despliegue a proposito.
  EOT
  type        = string
}

variable "google_client_id" {
  description = "ID de cliente OAuth. Es publico por diseno; no es un secreto."
  type        = string
  default     = ""
}

variable "api_key_ttl_days" {
  description = "Vida de la API key de sesion, en dias. 0 = sin expiracion."
  type        = number
  default     = 90
}

variable "min_instances" {
  description = <<-EOT
    Instancias siempre encendidas de Cloud Run.

    0 es la razon de elegir Cloud Run: sin trafico no se paga. El costo es un
    arranque en frio de un par de segundos en la primera peticion. Subirlo a 1
    lo elimina y agrega un contenedor corriendo 24/7 a la factura.
  EOT
  type        = number
  default     = 0
}

variable "max_instances" {
  description = "Tope de escalado. Tambien es el tope de gasto si algo se dispara."
  type        = number
  default     = 4
}

variable "crea_registro" {
  description = <<-EOT
    Si este entorno es el dueno del Artifact Registry del proyecto.

    Hay un solo registro para todo el proyecto, pero esta config se aplica una
    vez por entorno. Exactamente un .tfvars debe traer true; los demas lo leen
    con un data source.

    Hoy lo tiene production, por ser el primero que se aplico. Si algun dia se
    destruye production, hay que pasarle el true a otro entorno ANTES, o el
    registro se va con las imagenes dentro.
  EOT
  type        = bool
  default     = false
}
