# Adjuntos del Diario

La migración 013 agrega metadatos de archivos a Postgres. Los bytes se guardan
fuera de la base. Aplicar con `fierro-api-migrate` antes de iniciar esta versión.
Se reservó 012 para el PR de búsqueda del Diario (#147).

## Desarrollo

Con `FIERRO_ENV=dev` y `FIERRO_MEDIA_BUCKET` vacío se usa `FIERRO_MEDIA_DIR`
(por defecto `/tmp/fierro-media`). Usar un directorio persistente o un volumen
para conservar archivos al reemplazar contenedores. Las descargas locales pasan
por la API y requieren la misma sesión y organización que la nota.

## GCS

Configurar `FIERRO_MEDIA_BUCKET` con un bucket **privado**, acceso uniforme y
prevención de acceso público. La API usa Application Default Credentials del
servicio. Necesita crear, leer y consultar metadatos de objetos. Las escrituras
usan `if_generation_match=0` y nunca reemplazan un objeto existente.

Para firmar sin archivo de claves, habilitar IAM Service Account Credentials y
dar a la identidad de la API `iam.serviceAccounts.signBlob` sobre la cuenta
firmante (por ejemplo, Service Account Token Creator sobre sí misma). La URL
firmada V4 dura cinco minutos y fija la generación del objeto. No registrar
URLs firmadas completas en logs ni guardarlas como referencia permanente.

En stage/production, la ausencia del bucket produce 503 al solicitar adjuntos.
La recepción de pesajes sigue disponible. No hay respaldo a disco efímero.
`infra/terraform/media.tf` declara el bucket por entorno y los permisos mínimos
de la API. Revisar el plan antes de aplicarlo. Este cambio no se ha aplicado en
la nube; configurar GCS y probar la firma con la identidad desplegada sigue
siendo parte de la puesta en marcha.

## Límites y recuperación

Cada nota admite seis fotos y dos audios, hasta 2 MiB por archivo. Fotos JPEG o
WebP, hasta 1024 px por lado; la API decodifica y vuelve a codificar sin EXIF.
Audios WebM/Opus o MP4/AAC, sin video, hasta 120 segundos medidos al decodificar.
La extensión del nombre nunca determina el tipo.

Crear primero la nota y después enviar multipart a
`POST /v1/journal/{entry_id}/attachments` con `attachment_id`, `kind` y `file`.
Las rutas equivalentes bajo `/v1/animals/{tag}/journal/...` verifican también
la asociación del animal con la nota. Reintentar con los mismos UUID y bytes.
Un mismo UUID con otros bytes devuelve 409. El almacenamiento es inmutable y
permite reconciliar una escritura de objeto cuya transacción SQL no se confirmó.
Un fallo permanente puede dejar un objeto privado sin metadatos; cualquier
limpieza futura debe comparar con Postgres y respetar los reintentos en curso.

El listado del Diario incluye solo metadatos. Para visualizar un adjunto,
consultar su endpoint individual con credencial; devuelve una URL firmada o una
ruta local autenticada. Las respuestas de localización usan `private, no-store`.
Los secretos y las claves internas del objeto no forman parte de las respuestas.
