# Bitácora de relevo: dashboard de Fierro

Actualización 2026-09-25: dirección visual aprobada e implementada localmente;
ver [avance y evidencia del panel](dashboard-progress.md). El inventario inferior
describe el estado anterior a esa implementación.

Fecha de corte: 2026-09-25. Base inspeccionada: `03358ad`.
Objetivo del próximo trabajo: diseñar e implementar por etapas el dashboard
autenticado para consultar y administrar datos reales, manteniendo la identidad
del home y de Entrar. Este documento es un relevo, no una autorización para
desplegar, modificar producción ni completar todas las etapas de una vez.

## 1. Leer primero

1. [Reglas del repositorio](../AGENTS.md) y [guías de agentes](agent/README.md).
2. [Especificación funcional de Pesajes](frontend-pesajes.md): fuente de verdad
   para estructura, textos, estados, datos y criterios de esa pantalla.
3. [Desarrollo incremental](agent/frontend-self-driven.md) y skills del repo
   `fierro-engineering-rules` y `fierro-frontend-self-driven`.
4. [Contrato de datos](data-contract.md), [OpenAPI versionado](contracts/openapi.json)
   y [arquitectura](architecture.md). Contrastar con código y API del entorno:
   un contrato versionado no demuestra que producción ya lo implemente.
5. [Diseño de Entrar](design/entrar.md), [home](frontend-home.md) y
   [bitácora del home](frontend-home-progress.md).

Consultar primero el grafo MCP para descubrir código. Revisar `git status`
y preservar cambios ajenos antes de comenzar. Las notas antiguas del home
son históricas: no describen por sí solas el estado actual del despliegue.

## 2. Estado entregado y verificado

- PR [#68](https://github.com/zaned897/fierroid/pull/68) fusionado. Al cierre de
  la publicación, `main`, `stage` y `production`, locales y remotas, apuntaban
  a `03358ad2604cc915f3bcdf4ddc16c3126e5175aa`. Revalidar antes de trabajar.
- Frontend publicado: <https://fierroid.vercel.app>.
- Acceso: <https://fierroid.vercel.app/entrar>. Nombre visible: **Entrar**.
  Se corrigió el 404 de acceso directo mediante rewrite específico en Vercel.
- Home: portada, Cómo funciona, Beneficios, FAQ, cierre, transición del paisaje
  y animación de gráfica implementados. La gráfica pública contiene ejemplos;
  no es una gráfica del dashboard conectada a los datos de un cliente.
- El rediseño completo de Historial del home y su integración final siguen
  como pendientes separados; no confundirlos con el historial privado.
- El usuario aprobó visualmente Entrar. Se conservaron Google y el flujo de
  sesión; no se añadieron contraseñas ni registro abierto.
- CI pasó en las tres ramas: Python, web, smoke Docker y guardia de promoción
  cuando corresponde. Vercel y publicación de imágenes completados.
- Se comprobó Entrar público a 390 y 1440 px, sin desbordamiento, con botón de
  Google y `/v1/auth/config` respondiendo 200. Localmente también a 375 y 768 px.
- **No se probó un inicio de sesión real ni el dashboard autenticado en este
  ciclo.** El build correcto no sustituye esa prueba.
- No se desplegó de nuevo Cloud Run ni se ejecutaron migraciones. Sincronizar
  ramas o publicar imágenes no significa que la API viva cambie de versión.

## 3. Usuarios de prueba: estado operativo, no fixtures

En producción se creó la organización `bitelemetric-pruebas`, nombre
**Bitelemetric (pruebas)**, con dos usuarios normales activos. El tercer usuario
solicitado ya estaba activo como superusuario y se conservó sin cambios.
Se verificaron roles y organización después del commit de la transacción.

No se crearon ranchos, estaciones ni pesajes para esa organización: una pantalla
vacía es un resultado esperado. No copiar datos de otra organización para
rellenarla. Los correos no se reproducen en esta bitácora versionable: consultarlos
con el responsable o mediante administración autorizada. No guardar credenciales,
DSN, tokens ni sesiones en documentación, fixtures, capturas o commits.

El acceso es por Google, incluidos correos corporativos asociados a una cuenta
de Google. El alta no equivale a verificar que cada persona haya iniciado sesión.
No usar estas cuentas ni crear datos en producción como prueba automática sin
autorización específica; preferir entorno local y fixtures aislados.

## 4. Mapa de implementación actual

| Archivo | Responsabilidad actual / punto de continuidad |
|---|---|
| `apps/web/src/App.jsx` | Sesión, rutas públicas mínimas, pestañas privadas y componente `Pesajes` |
| `apps/web/src/auth.js` | API key revocable, almacenamiento de sesión, `apiFetch`, Google y logout |
| `apps/web/src/Animales.jsx` | Lista, ficha, edición de alias/notas y subida de foto |
| `apps/web/src/photo.js` | Reducción de imágenes y descarga autenticada de fotografías |
| `apps/web/src/Admin.jsx` | Organizaciones, ranchos, asignación de estaciones y usuarios; solo superusuario |
| `apps/web/src/Marca.jsx` | Marca canónica: reutilizar, no reemplazar por un logo dibujado |
| `apps/web/src/Login.jsx`, `entrar.css` | Referencia reciente de identidad y acceso; preservar |
| `apps/web/src/VistaPesajesDemo.jsx` | Referencia de composición, con datos ficticios del home; no usar como fuente real |
| `apps/web/src/styles.css` | Estilos heredados compartidos; evitar regresiones por selectores globales |
| `apps/api/src/fierro_api/main.py` | Rutas y autorización; comprobar parámetros soportados |
| `apps/api/src/fierro_api/store_pg.py`, `animals.py`, `admin.py` | Lecturas, animales y relaciones administrativas |

Hoy `Pesajes` consulta `/v1/readings?limit=40` y `/v1/devices` cada 3 segundos,
permite actualizar manualmente y paginar con cursor. Muestra cola, versión y
estación junto al contenido principal. Todavía no tiene la composición aprobada
de último pesaje + cinco lecturas recientes.

Las pestañas privadas son estado React (`pesajes`, `animales`, `admin`), no rutas
independientes. No existe una pantalla privada separada de Estaciones o Historial
en `App.jsx`. No enlazar rutas inexistentes. Si se crean rutas, probar entrada
directa, recarga, atrás/adelante y rewrites de Vercel.

Operaciones ya consumidas: GET de lecturas/dispositivos/animales; PUT de metadatos
del animal; fotografía; GET/POST de organizaciones y usuarios; POST de ranchos;
PUT de asignación de dispositivo y DELETE de usuario. Inspeccionar métodos,
parámetros, autorización y respuesta antes de reutilizar cada operación.

## 5. Riesgos que debe cubrir el próximo ciclo

Hallazgos de lectura de código, no todos reproducidos en runtime:

- El refresco reemplaza la lista y el cursor: puede borrar lo cargado mediante
  «Ver más antiguas». Separar recientes e historial o definir una reconciliación.
- `setInterval` no impide solicitudes solapadas. Controlar respuestas tardías,
  desmontaje, errores y cambios de contexto; no mezclar datos entre usuarios.
- La ficha se selecciona actualmente por `tag_id`; revisar colisiones cuando un
  superusuario ve varias organizaciones. Identidad visual y operaciones deben
  conservar organización + identificador completo.
- Las escrituras del animal envían `org`; revisar también lectura de foto y
  detalle para superusuario. No asumir que la organización se infiere del tag.
- No asumir filtros por fechas o rancho solo porque figuren en un mockup.
  Confirmar API; si faltan, registrar la necesidad y acordar otra etapa.
- No representar un peso ausente como cero ni ocultar `stable` o procedencia de
  prueba. El slug de la organización no es evidencia suficiente de que cada
  lectura sea sintética.
- La pertenencia de lecturas se deriva de estación → rancho → organización.
  Reasignar una estación puede mover la visibilidad de su historia: no tratarlo
  como una edición cosmética ni hacerlo para poblar una demostración.
- Ocultar Administración no es seguridad. La API debe negar acceso no autorizado;
  probar aislamiento con dos organizaciones y credenciales de prueba locales.

## 6. Dirección de diseño y decisiones pendientes

Mantener Inter, marca original, bosque `#143c2d`, marfil `#f7f8f3` y petróleo
`#176575` como referencia reciente. La especificación de Pesajes todavía menciona
acentos ocres: **proponer y confirmar su alineación con esta paleta antes de
reescribir la especificación**. No presentar esta propuesta como aprobación final.

Prioridad: peso → animal → fecha/hora; información técnica en Estaciones.
Escritorio con lateral, móvil con navegación inferior según Pesajes. Mantener
Administración para superusuarios y funciones equivalentes en ambos tamaños.
Usar iconos con etiquetas; animación discreta y compatible con movimiento reducido.
No trasladar fotografías grandes de marketing al panel de operación.

Confirmar también: contexto inicial de superusuario; organización frente a
rancho; zona horaria; criterio de vigencia para «Conectado»; filtros disponibles;
alcance y rutas de Historial/Estaciones. Exportaciones, edición o eliminación de
pesajes, alertas y métricas nuevas no están aprobadas por este relevo.

## 7. Plan incremental propuesto

Cada etapa debe cerrar con evidencia y relevo; máximo tres resultados verificables.

| Etapa | Entrega | Cierre mínimo |
|---|---|---|
| 0. Inventario y diseño | Contrastar API real, permisos y especificación; proponer composición y resolver decisiones | Mapa de capacidades y diseño acotado aprobado |
| 1. Estructura privada | Contenedor, navegación y cuenta; conservar destinos existentes | Móvil/escritorio y sesión sin regresiones |
| 2. Pesajes | Último pesaje y cinco recientes con datos reales | Orden por captura, vacíos/errores/inestables y sin duplicados |
| 3. Historial privado | Destino funcional y paginación; filtros solo soportados | Refresco no pierde páginas ni cambia contexto |
| 4. Animales | Pulido de lista/ficha, notas y fotos | Operaciones conservan organización y muestran fallos |
| 5. Estaciones | Estado y detalle técnico fuera del resumen | Distingue conexión API de estado de equipo |
| 6. Administración | Pulido de herramientas existentes | Roles, confirmaciones e impacto de asignaciones verificados |
| 7. Integración | Accesibilidad, rendimiento y regresiones | Evidencia completa y autorización separada de publicación |

**Primera acción recomendada:** ejecutar la etapa 0, sin modificar producción.
No comenzar por rehacer todo `App.jsx` ni instalar una biblioteca de dashboard.
Crear una rama `codex/dashboard-…` desde `main` actualizado para cambios de producto.

## 8. Entorno y verificación

Última configuración local conocida (comprobar antes de arrancar servicios):
web `127.0.0.1:5173`, API Fierro `127.0.0.1:18000`, PostgreSQL Fierro `15432`.
El proyecto EHS usa otros contenedores y puertos; no detenerlos ni cambiarles la
configuración. El proxy local de Vite apuntaba a la API de Fierro en 18000.
No copiar `.env` ni presumir que estos procesos siguen vivos un nuevo día.

Comandos estándar desde `apps/web`: `pnpm lint` y `pnpm build`.
En sesiones previas el wrapper pnpm falló con
`ERR_PNPM_ABORTED_REMOVE_MODULES_DIR_NO_TTY`; se verificó mediante
`node_modules/.bin/eslint.cmd src --max-warnings 0` y
`node_modules/.bin/vite.cmd build`, sin reinstalar dependencias.
Para CI y pruebas de backend seguir [testing.md](agent/testing.md).

Matriz mínima para cada unidad afectada:

- 375, 390, 768 y 1440 px; teclado, foco, controles de 44 px, contraste y
  ausencia de desbordamiento. Guardar capturas sin datos personales.
- Carga, vacío, API caída, respuesta tardía, red restablecida, 401, 403 y sesión
  cerrada. Sin datos de la cuenta anterior ni pesos ficticios.
- Usuario normal, superusuario y dos organizaciones con tags repetidos.
- Capturas sincronizadas tarde, `event_id` repetido y peso inestable.
- Actualización automática durante paginación, edición y cambio de contexto.
- Entrada/salida de sesión reales con cuenta de prueba autorizada. Separar
  pruebas con fixtures de evidencia del flujo real.

No afirmar «terminado» por compilar. Registrar qué se ejecutó, qué no y por qué.

## 9. Publicación y límites

Flujo documentado: feature → PR a `main` → fast-forward a `stage` → fast-forward
a `production`, sin force-push ni commits exclusivos de ramas de entorno.
**Vercel publica el frontend de producción al fusionar en `main`**: solicitar
autorización antes del merge; no asumir que `main` es solo un entorno de prueba.
Cloud Run se despliega por otro proceso. Los previews tienen un rewrite de API
hacia stage; comprobar que esa API esté operativa antes de prometer pruebas allí.

No repetir altas de usuarios, migraciones o promociones solo porque aparezcan
en esta bitácora. La petición actual autoriza documentación de relevo.
Los archivos ajenos sin seguimiento (worktrees, Pipfile, capturas de hardware y
recursos de favicon) deben permanecer intactos.

## 10. Plantilla de cierre del siguiente agente

- Fecha, rama y commit base:
- Unidad y criterio abordados:
- Decisiones confirmadas / pendientes:
- Archivos modificados:
- Pruebas ejecutadas y evidencia:
- Limitaciones y problemas reproducidos:
- Estado: terminado / parcial / bloqueado:
- Próxima unidad y autorización necesaria:

### Registro de esta entrega

2026-09-25: se redacta este relevo con inspección de código y grafo. No se
modificó la aplicación, la API ni producción. El dashboard aún requiere diseño,
implementación incremental y validación autenticada.
