# Panel privado: implementación de la dirección visual

Fecha: 2026-09-25. Rama: `codex/dashboard-style`. Base: `03358ad`.
Solicitud: implementar la imagen aprobada reutilizando lo existente.
Estado: implementado localmente; pendiente revisión del usuario con su sesión.
Sin commit, publicación, migraciones ni generación de nuevos pesajes.

## Unidades y resultados

1. Contenedor privado: `Dashboard.jsx` y `dashboard.css`, marca canónica,
   Inter, bosque/marfil/petróleo, lateral de escritorio, barra inferior móvil,
   menú Más y Cuenta con cierre de sesión. ESLint y build pasaron tras esta unidad.
2. Pesajes: componente extraído de App, último pesaje y cinco recientes,
   pesos ausentes sin ceros ficticios, fecha completa en hora del dispositivo,
   etiquetas para `mock`/`synthetic` e inestables. Consulta de recientes cada
   30 segundos en pestaña visible; sin solapar solicitudes, aborto al salir y
   timeout de 15 segundos. Se reutiliza `apiFetch` y la autorización existente.
3. Destinos: Historial usa la paginación existente de 40 en 40; es una
   instantánea sin polling mientras se lee hacia atrás. Estaciones muestra
   los reportes existentes, cola y versión; no infiere conexión del equipo.
   Animales y Administración conservan formularios y operaciones con tema local.

## Decisiones y límites de la API

- La API ordena por captura e identificador del evento; el cliente deduplica por
  `event_id`, conservando pesajes distintos de un mismo animal.
- `/v1/readings` y `/v1/devices` no admiten selector de organización. Se conserva
  el contexto real: todas para superusuario, la asignada para usuario normal.
  No se implementó el selector del mockup ni filtros de rancho/fecha ficticios.
- Las vistas siguen siendo estado React. No se crearon rutas ni rewrites nuevos.
- El texto de última consulta es una fecha de consulta exitosa, no una promesa de
  conexión de la estación. Historial conserva la instantánea hasta cambiar de vista.
- Un 503 conserva los datos con advertencia; un 403 los retira y muestra el error.
  Un 401 usa el cierre por sesión expirada existente.
- No se enlaza un arete desde Pesajes: la respuesta de lecturas no contiene la
  organización necesaria para elegir inequívocamente su ficha como superusuario.

## Corrección reproducida en Animales

Con dos organizaciones y el mismo tag, elegir la segunda ficha abría la primera.
Reproducido en navegador con fixtures, corregido seleccionando por organización
y tag. La organización se muestra en la ficha y en la lista del superusuario.
La descarga de fotos también envía `org`, como ya hacían las escrituras.
No se modificaron los permisos del servidor.

## Evidencia

- ESLint directo: `node_modules/.bin/eslint.cmd src --max-warnings 0`, pasó.
- Build: `node_modules/.bin/vite.cmd build`, pasó (sin dependencias nuevas).
- `node --test tests/readings.test.mjs`: 3 pruebas pasan. Orden por captura ante
  sincronización tardía, duplicados de evento, pesajes del mismo animal,
  pesos ausentes y procedencia de prueba.
- Navegador: 375, 390, 768 y 1440 px sin desbordamiento horizontal en Pesajes.
  Administración revisada a 375/768 px. Navegación móvil con blancos de 60 px;
  cuenta accesible con Enter y foco visible; cambio de vista enfoca el título.
- Historial: 40 → 80 filas; las 80 permanecen y no hay consultas nuevas durante
  más de un intervalo de refresco. Acceso móvil a Historial y Administración.
- Estados: vacío, 503 con datos, recuperación, 403 con retirada de filas, 401,
  respuesta lenta con botón deshabilitado y navegación durante la solicitud.
- Usuario normal: no hay controles de Administración. Superusuario: sí.
- Ficha con tag repetido: se verificó organización `otra` y peso 300.0, frente a
  `ejemplo` y 437.5. Fixtures de prueba, no datos del usuario.
- Home y Entrar inspeccionados nuevamente; conservan su diseño.
- Sin errores o avisos en consola durante la revisión del panel.
- [Escritorio 1440](design/dashboard-evidence/desktop-1440.png) y
  [móvil 390](design/dashboard-evidence/mobile-390.png): capturas del frontend
  implementado, con fixtures explícitos y correo reservado `example.test`.
  El harness temporal fue retirado; no guardó sesiones ni llamó al backend.
- El simulador sigue detenido: `Running=false`, `RestartPolicy=no`.

## No verificado

- Inicio de sesión OAuth y escrituras reales de fotos, notas o administración.
  El usuario inició sesión en un navegador externo que no está expuesto a estas
  herramientas. Usar `http://localhost:5173`, no `127.0.0.1`, por el origen OAuth.
- Aislamiento de organizaciones probado aquí en presentación con fixtures;
  no reemplaza las pruebas de autorización de la API.
- Ruff y pytest se intentaron con el Python local: faltan ambos módulos.
  No se cambió código Python ni se instalaron herramientas para este trabajo visual.
- Permanecen pendientes los filtros por organización/rancho, rutas privadas
  independientes y una revisión funcional completa de administración.

Siguiente paso: revisión visual del usuario en localhost con sus datos locales.
