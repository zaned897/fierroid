# Lista de espera en Google Sheets (#129)

La base es la fuente de verdad. Un job copia las altas nuevas a una hoja para el
equipo comercial; el registro (`POST /v1/waitlist`) nunca llama a Google.

## Cómo funciona
- `python -m fierro_api.waitlist_sheet` copia las filas con `id` mayor al cursor
  `waitlist_export.last_id` (migración `009`) y solo avanza el cursor si Google
  confirma. Dos corridas seguidas no duplican; si Google falla, el error queda en
  logs, el job sale con código 1 y la siguiente corrida reintenta.
- Columnas: `id, fecha, nombre, correo, estaciones, consentimiento`. Se envían
  con `valueInputOption=RAW`, así que un nombre que empieza con `=` no se
  ejecuta como fórmula.

## Configurar (una vez, a mano)
1. Crear la hoja con una pestaña llamada `Lista` y la fila de encabezados de arriba.
2. Crear un Cloud Run Job con la misma imagen de la API, comando
   `python -m fierro_api.waitlist_sheet`, y una cuenta de servicio propia.
3. Compartir la hoja **solo** con el correo de esa cuenta de servicio (editor)
   y con las personas autorizadas del equipo comercial.
4. Variables del job: `FIERRO_API_DSN` (el mismo secreto que la API) y
   `FIERRO_WAITLIST_SHEET_ID` (el id de la URL de la hoja).
5. Cloud Scheduler: cada 15 minutos.

No hay llave JSON: el token sale del servidor de metadatos de Cloud Run con el
scope de Sheets. Habilitar la API de Google Sheets en el proyecto.

## Probar
```
ruff check apps && pytest apps/api -q   # con FIERRO_TEST_PG_DSN apuntando a Postgres local
```
