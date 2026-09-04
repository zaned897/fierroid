output "api_url" {
  description = "URL publica de la API. Va en FIERRO_API_URL del agent y en VITE_API_BASE de la PWA."
  value       = google_cloud_run_v2_service.api.uri
}

output "registro_docker" {
  description = "Destino de las imagenes. Cloud Run no despliega desde GHCR."
  value       = "${var.region}-docker.pkg.dev/${var.project_id}/${google_artifact_registry_repository.images.repository_id}"
}

output "instancia_sql" {
  description = "Nombre de conexion de Cloud SQL, para el proxy local."
  value       = google_sql_database_instance.principal.connection_name
}

output "job_migraciones" {
  description = "Comando para aplicar migraciones tras cada despliegue."
  value       = "gcloud run jobs execute ${google_cloud_run_v2_job.migrate.name} --region ${var.region} --wait"
}

output "origenes_cors" {
  description = "Recordatorio: la PWA debe servirse desde uno de estos origenes."
  value       = var.cors_origins
}
