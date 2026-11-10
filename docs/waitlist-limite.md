# Límite de abuso de la lista de espera (#74)

## Decisión
La URL de Cloud Run es pública, así que cualquier encabezado que mande el
cliente (`X-Forwarded-For`, `X-Real-IP`) se puede inventar. La identidad del
cliente sale de dos fuentes que el cliente no controla:

1. **Por Vercel** (el caso normal): `apps/web/middleware.js` toma `x-real-ip`
   (lo pone Vercel) y lo reenvía como `x-fierro-client-ip` junto con
   `x-fierro-edge` = `FIERRO_EDGE_SECRET`. La API solo cree en la IP si el
   secreto coincide.
2. **Directo a Cloud Run**: la última entrada de `X-Forwarded-For`, que agrega
   el frente de Google con la IP que se conectó.

## Límites
- **Por cliente:** 5 intentos por hora (altas nuevas o reintentos de un correo
  existente). Un upsert en `waitlist_rate`, antes del lock y de cualquier otra
  consulta: el abuso se rechaza barato. 429 con `Retry-After: 3600`.
- **Global:** 100 altas nuevas por hora, de respaldo.
- Los dos viven en PostgreSQL, así que valen entre réplicas.
- La IP no se guarda: `waitlist_rate.client` es un HMAC con el secreto. Las
  ventanas de más de un día se borran solas.

## Configurar (una vez por entorno)
1. Generar el secreto: `openssl rand -hex 32`.
2. Vercel → Settings → Environment Variables: `FIERRO_EDGE_SECRET` (Production
   y Preview con el valor de cada entorno).
3. Cloud Run: la misma variable `FIERRO_EDGE_SECRET` en `fierro-api-stage` y
   `fierro-api-production` (ideal en Secret Manager, como la de Anthropic).
4. Correr la migración `010` con `fierro-migrate-<entorno>`.

Sin el secreto **no hay límite por cliente** (solo el global de 100/h): si lo
hubiera, todos los que llegan por Vercel compartirían la IP de salida de Vercel
y se bloquearían entre sí. El límite por cliente se activa solo al configurar
el secreto en los dos lados.
