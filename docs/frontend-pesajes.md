# Frontend: especificación funcional de Pesajes

Estado: propuesta funcional acordada; implementación pendiente.
Fecha: 2026-09-22.
Referencia: rediseño aprobado en conversación, basado en la primera propuesta
visual de Fierro con menos información. Este documento es la referencia textual
versionada; los ejemplos no son datos que deban quedar fijos en la aplicación.

## Objetivo y alcance

Permitir que una persona en el rancho identifique rápidamente qué animal se
pesó, cuánto pesó, a qué hora y cuáles fueron las lecturas anteriores.
La captura es automática: no agregar un botón para guardar pesajes.

Alcance: pantalla de Pesajes en escritorio y móvil. Animales, Estaciones e
Historial son destinos funcionales; su diseño completo requiere especificaciones
propias. No se cambia el contrato de la API ni la lógica de captura del agente.
La navegación descrita es un objetivo de producto, no una afirmación de que todas
estas vistas ya existan. Si falta un destino, implementar un acceso funcional o
acordar una entrega por etapas; no dejar botones sin efecto.

## Estructura

1. Encabezado: marca, contexto seleccionado y cuenta.
2. Título e indicadores discretos de conexión y prueba.
3. Tarjeta del último pesaje.
4. Lecturas recientes.
5. Acceso al historial.

Escritorio: barra lateral de navegación. Móvil: navegación inferior.
Conservar la identidad visual aprobada: verde oscuro, fondo marfil, acentos
ocres discretos, bordes suaves y espacios suficientes. Prioridad visual:
peso, animal, hora. Evitar ilustraciones grandes, métricas accesorias y paneles
que compitan con las lecturas.

## Etiquetas de navegación y encabezado

| Etiqueta | Descripción y comportamiento |
|---|---|
| FIERRO | Marca de la aplicación. |
| Pesajes | Pantalla principal; último pesaje y lecturas recientes. |
| Animales | Listado de animales y acceso a sus fichas. |
| Estaciones | Estado de los equipos y detalles técnicos. |
| Los Encinos | Ejemplo del contexto seleccionado; usar el nombre real. |
| Cuenta | Nombre accesible del control de perfil. Mostrar el nombre real si está disponible. |
| Cerrar sesión | Acción en el menú de cuenta; conservar el comportamiento seguro existente. |

Distinguir organización y rancho según el modelo existente. No llamar rancho a
una organización. Cuando solo existe un contexto autorizado, mostrar su nombre
sin desplegable. Mantener accesibles las funciones administrativas para quienes
tienen permiso; el mockup representa la vista de usuario final, no su eliminación.

## Indicadores de estado

Título de la pantalla: **Pesajes**.

| Etiqueta | Condición y significado |
|---|---|
| Conectado | La consulta a la API funciona y los datos están actualizados según el criterio explícito de vigencia definido al implementar. |
| Reconectando… | Se intenta recuperar la comunicación; conservar las últimas lecturas conocidas. |
| Sin conexión | El navegador no tiene conexión de red; no puede actualizar las lecturas. |
| No se pudo actualizar | Falló la consulta aunque puede existir red; la información visible puede estar desactualizada. |
| Modo de prueba | El contexto completo está configurado como prueba. Si hay datos mezclados, identificar individualmente las lecturas de prueba. |

Conectado describe la comunicación de la pantalla con la API, no el estado de
todos los lectores o básculas. El estado de cada equipo pertenece a Estaciones.
No determinar la conectividad solo con navigator.onLine: una consulta fallida
requiere un estado de error aunque el navegador indique que tiene red.
No usar únicamente color para comunicar estados.

## Tarjeta del último pesaje

Título: **Último pesaje**.

| Elemento | Ejemplo | Regla |
|---|---|---|
| Peso | 437.5 kg | Dato dominante; unidad visible y un decimal. |
| Animal | Animal BEDE50D3 | Nombre o identificador disponible, sin inventar información. |
| Fecha y hora | Hoy, 19:42 | Momento de captura, no de sincronización. |
| Indicador de prueba | Modo de prueba | Aquí cuando solo esta lectura es de prueba; evitar repetir la etiqueta global. |

- Seleccionar la lectura más reciente por fecha de captura del contexto actual.
- Una lectura antigua sincronizada tarde no desplaza otra capturada después.
- Actualizar automáticamente sin mover el foco del usuario.
- Abrir la ficha desde la identificación si existe un destino funcional.
- Conservar la última lectura ante un error e indicar su posible desactualización.
- No presentar una lectura antigua como confirmación de una nueva captura.
- No agregar grandes confirmaciones, instrucciones del siguiente animal o un
  botón de guardar; no están en el diseño aprobado.

El identificador completo del ejemplo es `proto:BEDE50D3`. Puede mostrarse
`BEDE50D3` con una indicación de prueba, pero búsquedas, enlaces y operaciones
conservan el identificador completo. La identidad del animal también debe
respetar su organización; no asumir que el tag es globalmente único.

## Lecturas recientes

Título: **Lecturas recientes**. Mostrar hasta cinco lecturas, de más reciente
a más antigua, por fecha de captura y dentro del contexto seleccionado.

| Columna | Contenido | Ejemplo |
|---|---|---|
| Animal | Nombre o identificador. | BEDE50D3 |
| Peso | Peso registrado con unidad. | 437.5 kg |
| Hora | Hora de captura; incluir fecha si no es de hoy. | 19:42 |

Acción secundaria: **Ver historial**. Abrir el historial completo conservando
el contexto seleccionado.

- La primera fila puede coincidir con la tarjeta del último pesaje.
- Usar `event_id` como identidad y para deduplicar eventos recibidos.
- No deduplicar por animal, peso u hora: pueden ser capturas distintas legítimas.
- No incluir versión del agente, cola, identificador técnico de estación ni
  estado de sincronización en cada fila.
- Si se reciben lecturas inestables, mostrar **Peso inestable**. Simplificar la
  pantalla nunca debe ocultar esta condición.
- En móvil conservar los tres datos; usar una lista si la tabla exige scroll
  horizontal. Un icono pequeño de animal puede acompañar al texto, no sustituirlo.

## Carga, estados vacíos y errores

| Situación | Texto principal | Texto secundario o acción |
|---|---|---|
| Carga inicial | Cargando pesajes… | Estructura provisional sin pesos ficticios. |
| Sin lecturas | Aún no hay pesajes | Los pesajes aparecerán aquí cuando el equipo los envíe. |
| Historial sin resultados | No encontramos pesajes | Prueba con otro animal o cambia las fechas. Mostrar solo si existen esos filtros. |
| Error sin datos disponibles | No pudimos cargar los pesajes | Botón Reintentar. |
| Error con datos anteriores | No se pudo actualizar | Mostrando la última información disponible. |
| Sin conexión | Sin conexión | Los nuevos pesajes aparecerán cuando se restablezca la conexión. |
| Sesión caducada | Tu sesión terminó | Botón Iniciar sesión. |
| Contexto sin acceso | No tienes acceso a esta información | Elegir otro contexto autorizado, si existe. |

No representar datos ausentes como `0 kg`. No garantizar que el equipo sigue
capturando sin conexión desde esta pantalla si no existe evidencia de ello.
No mostrar datos de una sesión anterior al cerrar sesión o perder autorización.

## Datos requeridos

Reutilizar el [contrato de la API](contracts/openapi.json) y el
[contrato de datos](data-contract.md). Esta lista expresa necesidades lógicas;
no define nuevos endpoints ni campos obligatorios del backend.

| Dato | Uso |
|---|---|
| event_id | Identidad única de la lectura y deduplicación. |
| tag_id | Identificación completa del animal. |
| weight_kg | Peso mostrado. |
| captured_at | Orden y fecha/hora de captura. |
| stable | Advertencia de peso inestable cuando corresponda. |
| source | Distinguir fuentes de prueba según los valores reconocidos del contrato. |
| device_id | Relación con la estación; detalle fuera de la vista principal. |
| Contexto autorizado | Acotar por organización o rancho con el modelo y capacidades existentes. |
| Última consulta exitosa | Estado local del frontend para actualización y conectividad. |

No inventar nombres de animales, capacidades de filtros ni estados que la API
no proporciona. Los permisos deben aplicarse en la API además de en la interfaz.

## Actualización, formato e interacción

- Mantener el mecanismo de actualización existente; este rediseño no exige
  WebSockets. Evitar consultas simultáneas y reducir reintentos ante fallos.
- Al volver a la pestaña, consultar información actualizada.
- Al cambiar de contexto, descartar respuestas tardías del anterior. Nunca
  presentar lecturas anteriores bajo el nombre del nuevo contexto.
- Usar una zona horaria coherente. Antes de implementar, definir si proviene del
  rancho o del navegador y documentar la decisión; el mockup no define ese origen.
- Mostrar fecha completa en el detalle. Usar formato de hora de 24 horas.
- Mantener un formato numérico uniforme. La referencia muestra `437.5 kg`;
  preparar las etiquetas para localización sin cambiar el dato original.
- Al actualizar, no mover el foco ni interrumpir la interacción.

## Accesibilidad

- Texto legible y contraste suficiente; controles táctiles de al menos 44 × 44 px.
- Navegación con icono y texto, sección activa distinguible y foco visible.
- Nombres accesibles para perfil, selector y controles con solo icono.
- Evitar anuncios repetidos del lector de pantalla en cada consulta automática.
- Escritorio y móvil deben ofrecer las mismas funciones.

## Criterios de aceptación

- [ ] Último pesaje muestra peso, animal y hora reales.
- [ ] Lecturas ordenadas por captura, incluidas las sincronizadas tarde.
- [ ] Consultas repetidas no duplican eventos.
- [ ] Cambio de contexto respeta permisos y no mezcla respuestas ni datos.
- [ ] Errores conservan los datos autorizados anteriores e indican su estado.
- [ ] Lecturas de prueba e inestables se distinguen cuando corresponde.
- [ ] Cola, versión e identificadores técnicos no aparecen en la vista principal.
- [ ] Pesajes, Animales, Estaciones y Ver historial tienen destinos funcionales.
- [ ] Móvil funciona sin desplazamiento horizontal.
- [ ] Captura automática sin botón de guardar ni confirmaciones inventadas.
- [ ] Navegación por teclado, foco, contraste y controles táctiles verificados.

## Fuera de alcance

Rediseño completo de Animales, Estaciones, Historial o Administración; cambios
en drivers, outbox, sincronización, permisos del backend o despliegues. Los
indicadores y enlaces propuestos no autorizan a relajar los invariantes descritos
en la [arquitectura](architecture.md).
