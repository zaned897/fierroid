#!/usr/bin/env bash
# Cambia la imagen de la API en Cloud Run y comprueba que quedo corriendo.
#
#   deploy-api-cloud-run.sh deploy <stage|production> <imagen@sha256:...>
#   deploy-api-cloud-run.sh verify <stage|production> <imagen@sha256:...>
#
# Lo usa .github/workflows/deploy-api.yml, y sirve igual a mano con gcloud
# autenticado. Solo toca la imagen: el resto de la configuracion (secretos,
# variables, escalado) es de Terraform y aqui no se pisa.
#
# Orden de `deploy`: imagen del job -> migraciones -> imagen del servicio. Las
# migraciones van antes que el servicio porque el codigo nuevo puede necesitar
# el esquema nuevo; al reves habria un rato con la API respondiendo 500.
set -euo pipefail

REGION="${REGION:-northamerica-south1}"

uso() {
  echo "uso: $0 deploy|verify stage|production <imagen@sha256:...>" >&2
  exit 2
}

[[ $# -eq 3 ]] || uso
accion="$1"
entorno="$2"
imagen="$3"

case "$entorno" in stage | production) ;; *) uso ;; esac
# Digest, no etiqueta: con una etiqueta movil no se sabe que corre.
[[ "$imagen" == *@sha256:* ]] || {
  echo "La imagen debe ir por digest (…@sha256:…), no por etiqueta: $imagen" >&2
  exit 2
}

servicio="fierro-api-$entorno"
job="fierro-migrate-$entorno"

desplegar() {
  echo "Job $job -> $imagen" >&2
  gcloud run jobs update "$job" --region "$REGION" --image "$imagen" --quiet >&2

  echo "Migraciones ($job)" >&2
  gcloud run jobs execute "$job" --region "$REGION" --wait >&2

  echo "Servicio $servicio -> $imagen" >&2
  gcloud run services update "$servicio" --region "$REGION" --image "$imagen" --quiet >&2
}

verificar() {
  local corriendo url cuerpo intento
  corriendo=$(gcloud run services describe "$servicio" --region "$REGION" \
    --format='value(spec.template.spec.containers[0].image)')
  if [[ "$corriendo" != "$imagen" ]]; then
    echo "El servicio corre '$corriendo', se esperaba '$imagen'." >&2
    exit 1
  fi

  url=$(gcloud run services describe "$servicio" --region "$REGION" --format='value(status.url)')

  # /health devuelve el entorno: confirma que respondio el servicio correcto y
  # no solo uno vivo. Reintentos por el arranque en frio (min_instances = 0).
  for intento in 1 2 3 4 5 6; do
    if cuerpo=$(curl -fsS --max-time 20 "$url/health"); then
      if HEALTH="$cuerpo" ENTORNO="$entorno" python3 -c '
import json, os, sys
h = json.loads(os.environ["HEALTH"])
sys.exit(0 if h.get("ok") is True and h.get("env") == os.environ["ENTORNO"] else 1)
'; then
        echo "OK $url/health -> $cuerpo" >&2
        echo "url=$url"
        return 0
      fi
      echo "/health respondio algo inesperado: $cuerpo" >&2
      exit 1
    fi
    echo "Intento $intento: /health no responde todavia" >&2
    sleep 10
  done
  echo "$url/health no respondio tras varios intentos." >&2
  exit 1
}

case "$accion" in
  deploy) desplegar ;;
  verify) verificar ;;
  *) uso ;;
esac
