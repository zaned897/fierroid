# Animales: búsqueda e historial

2026-09-27. Publicado en stage mediante PR #69; producción no promovida.

## Entrega

- Búsqueda por nombre o arete sobre la lista existente, con conteo y estado sin resultados.
  La búsqueda se conserva al cerrar la ficha.
- Historial en páginas de 20: captura, recepción, estación, peso y procedencia de prueba.
  Actualización manual, cancelación al salir y timeout; no se reemplazan páginas por polling.
- Endpoint nuevo `GET /v1/animals/{tag_id}/readings`: usa la organización de la cuenta
  normal y exige organización explícita para superusuario. Contrato OpenAPI actualizado.
- Fuentes `proto-*` identificadas como lecturas de prueba.

## Validación

- 12 pruebas Python de ruta, API y contrato pasan. El test de la nueva ruta utiliza
  un store controlado: demuestra el alcance enviado al store, no sustituye integración Postgres.
- Ruff de Python modificado, ESLint y build web pasan; seis pruebas Node pasan.
- Navegador con fixtures locales: búsqueda por nombre y por arete, conservación de
  búsqueda al cerrar, selección de segunda organización con arete repetido,
  20 → 21 pesajes acumulados y desaparición de «Ver más» al finalizar.
- No se escribieron datos en stage ni producción. Harness temporal retirado.
- Pendientes: matriz responsive completa, errores de red en navegador e integración
  del endpoint con PostgreSQL y sesión real en stage.

## Validación previa a publicación

- 153 pruebas API pasan contra PostgreSQL 16 local aislado en puerto 25433.
  Incluye mismo arete en dos organizaciones, intento de elegir organización ajena,
  superusuario con organización explícita y paginación sin repetidos.
- Ruff de toda la API pasa.
- Revisión del panel completo con tamaños solicitados 375, 390, 768 y 1440:
  sin desbordamiento horizontal observado. El navegador aplica escala de viewport.
- Historial: error 503 visible y recuperación mediante Actualizar verificados.
- Evidencia móvil: `design/animal-history-mobile.png`, con datos ficticios locales.

## Publicación y continuación

Desplegar primero la API y después el frontend en stage. Una API anterior devuelve
404 y la ficha muestra «El historial aún no está disponible en esta API»; no se
recurre a consultas globales que puedan mezclar organizaciones.

Revisar esta entrega en stage antes de ampliar administración. Siguiente unidad:
mostrar organización y rancho de cada estación y sus últimos reportes, conservando
roles. Después abordar altas/asignaciones y, finalmente, emparejamiento de equipos.

## Publicación realizada

- PR: https://github.com/zaned897/fierroid/pull/69, integrado con CI exitoso.
- Main y stage: `33eee9f6f8f2821d401d2a2cd6fb856c5e7b3f23`.
- Production permanece en `06183897a80529666ce2463d6241c909558a2b1b`.
- API stage: revisión `fierro-api-stage-00002-zsc`, 100% del tráfico.
- Imagen verificada: `sha256:69e80bd099d6a52276515d48d0534bb0d71e8bf603bf44f799d111f6b0a9c79c`.
- Se actualizó solo la imagen del servicio mediante gcloud. Terraform instalado
  1.15.8 no satisface >=1.16; `stage.tfvars` local conserva el digest nuevo.
  No se aplicó Terraform, no se ejecutaron migraciones y el job de migración no cambió.
- Vercel: despliegue exitoso; alias stage devuelve `/health` 200 con `env=stage`.
  Bundle `index-DGgYmkb0.js` contiene búsqueda, historial y aviso STAGE.
- La API desplegada expone la nueva ruta en OpenAPI. La sesión real del navegador
  integrado sigue pendiente: muestra Entrar. Se pidió al usuario iniciar sesión.
- PostgreSQL temporal de pruebas detenido; contenedores de otros proyectos intactos.
