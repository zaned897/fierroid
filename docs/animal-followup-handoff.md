# Relevo activo: seguimiento de animales, gráfica y bitácora

Fecha: 2026-09-28. La entrega documental inicial se publicó en `main` (`d815089`).
Después, el usuario autorizó continuar en `codex/animal-followup`. La gráfica y
bitácora están implementadas y verificadas en esa rama; todavía no desplegadas.
Las secciones de infraestructura describen el último estado remoto verificado.

## Actualización de implementación

- Gráfica SVG individual sobre el historial cargado, eje temporal real, sin colapsar
  eventos distintos. Excluye pesos inválidos/inestables y pruebas por defecto;
  permite incluir pruebas con aviso. Cargar más historial amplía la gráfica.
- Bitácora paginada con fecha del evento, categoría, texto, autor autenticado y
  fecha de registro. Solo agregar/consultar; independiente de la nota general.
- GET/POST journal aislados por organización. UUID del cliente permite reintentar
  sin duplicados mientras la ficha sigue abierta; un contenido distinto con el
  mismo UUID devuelve 409. El formulario se limpia solo al recibir confirmación.
- Migración `007_animal_journal.sql` aplicada dos veces sin problemas solamente
  en PostgreSQL local aislado. Aplicarla en stage antes de publicar API/frontend.
- Validación: 161 pruebas API y 35 device-agent; Ruff; pruebas Node de gráfica,
  historial y fotos; lint/build web. Navegador local: filtrado de pruebas y nota
  conservada tras recargar. No se generaron lecturas en stage ni producción.
- Pendiente: publicar y verificar stage con sesión real; anomalías y resumen del
  hato siguen fuera de esta entrega. Los borradores no sobreviven cerrar la ficha.

El inventario de borradores de la sección 4 es histórico, anterior a esta
implementación. Los componentes nuevos son `EvolucionAnimal.jsx`, `animalTrend.js`
y `BitacoraAnimal.jsx`; el contrato OpenAPI y las pruebas están actualizados.

## 1. Objetivo aprobado y orden de trabajo

El usuario quiere seguimiento individual y general del ganado: seleccionar un
animal, consultar evolución del peso, identificar lecturas por revisar y registrar
anotaciones. Aprobó empezar por **gráfica individual + bitácora**, reutilizando la
ficha existente. Resumen del hato, reglas de anomalías, ranchos/estaciones y
emparejamiento vienen después, no deben incorporarse todos a esta unidad.

Primera acción del siguiente agente: leer AGENTS.md, docs/agent/README.md y este
documento; inspeccionar Git y el grafo antes de editar. Implementar y probar la
entrega de la gráfica y la bitácora, según la actualización inicial y la sección 5.
No arrancar simuladores para poblar stage.

Guías relevantes: [ingeniería](agent/engineering-rules.md),
[frontend incremental](agent/frontend-self-driven.md), [pruebas](agent/testing.md),
[desbloqueo](agent/unblock.md). Preferir codebase-memory-mcp para descubrimiento;
el índice puede estar atrasado: contrastar sus resultados con los archivos actuales.

## 2. Estado remoto verificado

Antes de subir este documento:

- `main` y `stage`: `33eee9f6f8f2821d401d2a2cd6fb856c5e7b3f23`.
- `production`: `06183897a80529666ce2463d6241c909558a2b1b`.
- PR [#69](https://github.com/zaned897/fierroid/pull/69) integrado.
- Web compartida de stage:
  https://fierroid-git-stage-eduardo-santos-projects-b48d5c7a.vercel.app/entrar
- API stage: https://fierro-api-stage-yj7cs5a7aq-pv.a.run.app
- Web de producción: https://fierroid.vercel.app
- Verificado hoy: `/health` del alias stage devuelve HTTP 200, `env=stage`.
  OpenAPI de stage contiene `/v1/animals/{tag_id}/readings`; **no contiene journal**.

Publicado con #69:

- Búsqueda por nombre/arete y conservación de búsqueda al cerrar la ficha.
- Historial individual paginado de 20 lecturas, con captura, recepción, estación,
  peso y etiquetas de inestable/prueba. Actualización manual.
- Endpoint de historial con alcance por organización: un usuario normal usa su
  propia organización; un superusuario debe indicar `org`.
- Fuentes `mock`, `synthetic` y `proto-*` identificadas como prueba.
- Corrección de foto con extensión incorrecta: un JPEG llamado `.png` se normaliza
  en cliente antes de subir; la API conserva su validación. El usuario confirmó que
  renombrar el archivo a `.jpg` resolvió su caso antes de publicar la corrección.
- Franja STAGE obtenida desde `/health`, también en Entrar. Fallo de consulta no
  se presenta como entorno confirmado.

**No están desplegadas aún** gráfica individual, bitácora, reglas de anomalías,
resumen general del hato ni alta autónoma de dispositivos por usuarios normales.

## 3. Infraestructura, acceso y hardware

- La UI de Vercel se inspeccionó: su rama de producción es **production**, no main.
  Notas antiguas del repositorio dicen main; no seguirlas sin verificar ajustes.
- Solo el host exacto `fierroid.vercel.app` reenvía a producción. Los demás hosts
  usan stage; `/v1` y `/health` siguen esa regla en `apps/web/vercel.json`.
- Con autorización explícita se exceptuó únicamente el alias estable de stage de
  Vercel Authentication. Otros previews siguen protegidos. El login de Fierro y
  sus permisos permanecen activos; lecturas sin sesión respondieron 401.
- El usuario confirmó que pudo iniciar sesión y ver datos en stage. No se confirmó
  el recorrido del nuevo historial con sesión real desde el navegador integrado:
  allí se observó Entrar. No afirmar que se probó todo el flujo autenticado.
- Los cuatro correos corporativos solicitados (miguel, arturo, eduardo, raul en
  `bitelemetric.com`) se crearon activos, normales y asociados a `los-encinos` en
  stage. Acceso por Google; no se generaron contraseñas. Ven los mismos datos de
  esa organización, incluidos datos sintéticos históricos. No duplicar las altas.
- Banco anterior: `rpi-los-encinos-001`. Nuevo Arduino + MFRC522 conectado a este
  PC: `rpi-los-encinos-002`, último puerto observado COM5. Antes se había reservado
  002 para Mac; ahora se utiliza en PC. No usar simultáneamente ese ID en otra máquina.
- El usuario confirmó captura de la tarjeta `proto:BEDE50D3` en stage. Es identidad
  de tarjeta, no de device. El peso proviene de potenciómetro, no de báscula real.
- Agente: backend `prototipo`, `FIERRO_MOCK_HW=0`, API stage. Outbox nueva:
  `%LOCALAPPDATA%/fierro-stage-station-002.db`; conservarla. La `.env` anterior sigue
  describiendo COM6/001 y otra SQLite: revisar antes de arrancar, no sobrescribir.
- No arrancar Docker mock ni seed contra stage/producción. El usuario pidió evitar
  datos periódicos artificiales y costos. Agentes reales envían heartbeats aunque
  no haya pesajes; verificar procesos actuales, no presumir que siguen ejecutándose.
- No tocar el contenedor del otro proyecto `ehs_saas_ai_api-db-1` (puerto 5432).
  Última API local Fierro: puerto 18000. El PostgreSQL de pruebas propio
  `fierro-history-test-pg` usa 127.0.0.1:25433 y quedó **detenido** al cerrar pruebas.

## 4. Inventario histórico anterior a la implementación

Checkout original: `C:/Users/eduardo/Documents/GitHub/fierroid`.
Rama actual al redactar: `codex/animal-followup`, creada desde `origin/main`.
El índice estaba vacío antes del commit documental; se preservaron estos cambios:

| Archivo | Estado y contenido |
|---|---|
| `apps/api/src/fierro_api/main.py` | Modificado sin commit: modelo JournalIn y GET/POST journal |
| `apps/api/src/fierro_api/journal.py` | Sin seguimiento: alta/listado con autor e idempotencia |
| `apps/api/src/fierro_api/migrations/007_animal_journal.sql` | Sin seguimiento: tabla e índice; **no aplicada** |
| `docs/animals-progress.md` | Registro local actualizado de publicación de #69 |
| `apps/device-agent/README.md` | Enlace local a guía Mac/Windows |
| `docs/stage-banco-mac-windows.md` | Guía local sin seguimiento; incluye supuesto Mac anterior |

No se ejecutaron lint, pruebas, migraciones ni regeneración del contrato para el
borrador de journal. No existe componente frontend de gráfica o bitácora todavía.

**Si continúas en esta misma máquina:** revisar y completar esos tres archivos de
API; no borrarlos ni sobrescribirlos. **Si continúas en otro clon:** no estarán allí;
puedes reconstruir la propuesta de la sección 5. El código publicado #69 es la base.

Hay además archivos ajenos/locales sin seguimiento: `.claude/worktrees/`, `Pipfile`,
capturas de hardware, recursos de favicon y evidencias de diseño. No usar `git add .`,
no limpiar el checkout ni subir capturas con sesiones/datos personales.

## 5. Diseño de la próxima unidad

### Gráfica individual

- Reutilizar los datos del historial de `HistorialAnimal.jsx`; ordenar por fecha de
  captura, conservar `event_id` y no colapsar pesajes distintos del mismo animal.
- Mostrar qué periodo y cuántos pesajes están cargados: inicialmente 20, no todo el
  historial. Al cargar más, ampliar la gráfica; no prometer cobertura completa.
- Eje temporal real, pesos ausentes nunca equivalen a cero. Tratar fechas inválidas,
  una única lectura, pesos iguales y sincronización tardía.
- Por defecto excluir fuentes de prueba y pesos inestables de la curva de seguimiento.
  Permitir incluir pruebas explícitamente, con aviso visible. Con los datos actuales
  puede quedar vacía: explicar por qué, nunca rellenar con pesos inventados.
- Mantener el listado accesible como alternativa a la gráfica. La interfaz debe
  funcionar con teclado y en móvil sin una dependencia gráfica innecesaria.

### Bitácora

- Independiente de `animals.notes`, que sigue siendo la nota general de la ficha.
- Cada entrada: fecha/hora del evento, categoría, texto, autor autenticado y fecha
  de registro del servidor. Categorías iniciales: observación, alimentación, manejo,
  salud; no convertir la categoría salud en diagnóstico automático.
- Primera versión append-only: agregar y consultar; sin editar/borrar silenciosamente
  entradas antiguas. Si hace falta corregir, agregar otra anotación explícita.
- Autor tomado de la sesión del servidor, nunca de un campo enviado por cliente.
- Alcance siempre organización + arete. Usuario normal no puede escoger otra org;
  superusuario debe especificarla. El mismo arete puede existir en dos organizaciones.
- Guardar requiere ACK: no mostrar éxito si hay timeout. Conservar el texto ante fallos.
  El cliente envía un UUID estable por intento lógico para reintentar sin duplicar.

Propuesta ya iniciada localmente (revisar antes de adoptarla):

```text
animal_journal
  entry_id UUID PRIMARY KEY                 # clave de idempotencia del cliente
  animal_id BIGINT FK animals(id) RESTRICT
  author_id BIGINT FK users(id) RESTRICT
  occurred_at TIMESTAMPTZ NOT NULL           # fecha del evento con zona
  created_at TIMESTAMPTZ DEFAULT now()
  category TEXT CHECK observacion/alimentacion/manejo/salud
  body TEXT CHECK longitud tras trim entre 1 y 4000
  índice (animal_id, occurred_at DESC, entry_id DESC)

POST /v1/animals/{tag_id}/journal?org=...
  {entry_id, occurred_at, category, body}
GET /v1/animals/{tag_id}/journal?org=...&limit=20&cursor=...
  {entries, next_cursor}
```

El borrador crea la ficha si no existe, dentro de la misma transacción del alta;
compara contenido/autor/ficha cuando hay conflicto de UUID y devuelve 409 si el
UUID corresponde a otro registro. Lista con cursor por (occurred_at, entry_id).
La respuesta propone entry_id, occurred_at, created_at, category, body y author
(nombre visible o correo). No expone claves ni credenciales.

Puntos que aún requieren pruebas/revisión: reintentos concurrentes, rollback ante
conflicto, aislamiento también en POST, fecha sin zona, UUID/cursor corrupto, texto
vacío y demasiado largo, desactivación del autor, ausencia de migración y errores de
red al guardar. Evaluar el efecto de RESTRICT en pruebas/limpieza; no relajar la
integridad solo para hacer pasar tests.

### Fuera de esta unidad

Reglas de cambios bruscos y periodos sin lecturas requieren umbrales acordados.
Presentarlas como «por revisar», no diagnósticos. Para el resumen general, excluir
pruebas por defecto. La estación/rancho donde se capturó una lectura **no demuestra**
la pertenencia actual del animal. No inventar ese vínculo en la base.

## 6. Mapa de código

- `apps/web/src/Animales.jsx`: lista, búsqueda, selección por organización+arete,
  ficha, notas generales y fotos.
- `apps/web/src/HistorialAnimal.jsx`: carga paginada, cancelación y timeout de 15 s.
- `apps/web/src/animales.css`: estilos acotados de historial.
- `apps/web/src/readings.js`: orden/deduplicación, fechas, peso, fuentes de prueba.
- `apps/web/src/photo.js`: normalización de formato, reducción y descarga autenticada.
- `apps/web/src/Entorno.jsx`: consulta única de entorno con timeout.
- `apps/api/src/fierro_api/main.py`: endpoints, `_write_scope`, autenticación.
- `apps/api/src/fierro_api/animals.py`: metadatos/fotos por organización.
- `apps/api/src/fierro_api/store_pg.py`: lecturas con filtros y cursor.
- `apps/api/src/fierro_api/migrate.py`: SQL numerado, transacción y advisory lock.
- `docs/contracts/openapi.json`: regenerar con `python -m fierro_api.contract`.

Riesgo preexistente observado y separado de esta entrega: `get_animal_photo`
no consume `org` para superusuario aunque el frontend lo envíe; `get_animal`
también elige el primer arete si su scope es global. No atribuir al historial esa
garantía para todas las rutas. Revisar aislamiento de esas lecturas antes de
presentar la ficha completa como segura ante aretes repetidos de superusuario.

## 7. Validación y publicación

La entrega #69 tuvo 153 pruebas API con PostgreSQL 16 aislado, Ruff, ESLint, build,
seis pruebas Node y CI verde. Se revisaron búsqueda, paginación 20→21, mismo arete
en dos organizaciones, recuperación de 503 y responsive. Eso **no valida journal**.

En esta máquina se creó un venv de herramientas en
`%TEMP%/fierro-stage-admin`. Puede reutilizarse; no contiene DSN de stage persistido.
Para pruebas, configurar explícitamente entorno dev y DSN de pruebas local, nunca
ejecutar fixtures/seed contra stage o producción. Comandos de referencia:

```powershell
# Desde la raíz; verificar que el contenedor propio conserve puerto 25433.
docker start fierro-history-test-pg
$env:FIERRO_ENV='dev'
$env:FIERRO_API_DSN=''
$env:FIERRO_TEST_PG_DSN='postgresql://postgres:fierro-local-test@127.0.0.1:25433/fierro_test'
& "$env:TEMP/fierro-stage-admin/Scripts/python.exe" -m pytest apps/api -q
& "$env:TEMP/fierro-stage-admin/Scripts/python.exe" -m ruff check apps/api
& "$env:TEMP/fierro-stage-admin/Scripts/python.exe" -m fierro_api.contract

cd apps/web
node --test tests/*.test.mjs
node_modules/.bin/eslint.cmd src --max-warnings 0
node_modules/.bin/vite.cmd build
```

Añadir pruebas de gráfica: exclusión de proto/mock/synthetic, pesos nulos, fechas,
orden y captura tardía; y pruebas PostgreSQL de la bitácora con dos organizaciones.
Probar formulario en navegador (doble clic, timeout/reintento, sesión expirada,
paginación y cambio de animal). Fixtures UI solo locales, nunca falsear capturas reales.

Último despliegue de API stage:

- Proyecto GCP `fierro-caw-scale`, región `northamerica-south1`.
- Servicio `fierro-api-stage`, revisión `fierro-api-stage-00002-zsc`.
- Imagen `northamerica-south1-docker.pkg.dev/fierro-caw-scale/fierro/fierro-api`
  con digest `sha256:69e80bd099d6a52276515d48d0534bb0d71e8bf603bf44f799d111f6b0a9c79c`.
- Terraform local 1.15.8 no cumple >=1.16; se actualizó solo la imagen del servicio
  mediante gcloud. `stage.tfvars` local guarda el digest; el job de migración quedó
  con su imagen anterior porque #69 no necesitaba migraciones.

**Journal sí necesita migración nueva**: construir/verificar imagen, revisar 007,
actualizar el job de stage antes de ejecutarlo (si se usa), migrar stage, desplegar
API y después frontend. No ejecutar el job antiguo esperando que conozca 007.
No promover production como consecuencia automática de terminar stage.
Registrar revisión, digest, contrato, migraciones y verificaciones al publicar.

Para navegador, el control por clic no activó algunos botones de Vercel; enfocar
el control y enviar Return funcionó. No repetir clics indefinidamente. La sesión
integrada de Fierro puede ser distinta de la sesión en el navegador externo.

## 8. Criterio de cierre

La ficha muestra una curva honesta del conjunto cargado y permite agregar/listar
anotaciones persistentes con autor y fecha, sin fuga entre organizaciones ni
duplicados al reintentar. Pruebas y contrato actualizados. Diferenciar claramente
implementado, probado localmente, publicado en stage y validado con sesión real.
Solo entonces continuar con indicadores del hato y reglas de revisión acordadas.
