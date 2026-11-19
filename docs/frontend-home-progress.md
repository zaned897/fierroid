# Relevo del frontend del home

## 2026-11-18 — Fotos y notas de voz del Diario (#145)

Rama `codex/bitacora-adjuntos-web`, sobre el Diario de #150 (`560e955`).
Primera unidad, captura y borrador. Foto desde cámara o galería, conversión a
JPEG de hasta 1024 px, seis fotos y dos audios por nota. MediaRecorder elige
Opus o MP4, pide 32 kbps y detiene antes de dos minutos. Cada archivo se limita
a 2 MiB. Texto, blobs, UUID y nota confirmada se recuperan desde el borrador
local; si el almacenamiento está bloqueado se avisa su limitación.

Segunda unidad, subida y consulta. Guarda primero la nota y después cada archivo.
Conserva los mismos UUID y bytes al reintentar después de perder una respuesta,
incluso tras recargar. La nota confirmada queda fija hasta completar sus archivos.
Galería ampliable con dialog nativo y reproductor de voz en Diario y ficha.
Los object URLs se revocan al salir; cambiar de animal u organización reinicia
el contexto. Cerrar sesión limpia los blobs del borrador.

Verificación con pnpm 10, ESLint, build, 35 pruebas de lógica y 20 de navegador.
Capturas de [375 px](design/diario/adjuntos-galeria-145-375.png),
[1440 px](design/diario/adjuntos-galeria-145-1440.png) y
[formulario](design/diario/adjuntos-formulario-145-1440.png).
Las pruebas comprueban pérdida de ACK y recarga, micrófono denegado, límite de
grabación, organización y teclado. El audio se codifica con MediaRecorder real
desde una fuente sintética de prueba. También se probó navegador → API de #144
→ Postgres y almacenamiento local con dos fotos y un audio reproducible.

Para integrar, #150 aporta los componentes compartidos y #144 los endpoints.
Pendiente de puesta en marcha, validación en celulares físicos y firma con la
identidad real de GCS. Próximas unidades, derivados #146 y asistente #148.

## 2026-11-18 — Diario del rancho (#150)

Pantalla local en `codex/diario-rancho-web`, desde `main` `a447512`.
Incluye notas por día local, filtros por periodo, animal y categoría, y una
ventana para notas generales o compartidas. Reutiliza los borradores de
bitácora y conserva el UUID al reintentar. La ficha muestra las notas
históricas y enlaza al Diario. El acceso al asistente prepara una pregunta con
el animal y periodo seleccionados para que el usuario la envíe.

Evidencia con API simulada y cuentas ficticias a
[375 px](design/diario/diario-150-375.png) y
[1440 px](design/diario/diario-150-1440.png), y ventana de
[nueva nota móvil](design/diario/nueva-nota-150-375.png).
Validación con pnpm 10, como CI. Lint, 32 pruebas de lógica, 14 pruebas de
navegador y build correctos. Siguientes unidades del Diario, búsqueda #147 y
adjuntos #144–#146.

## 2026-09-25 — Panel privado

El estilo aprobado del panel se implementó reutilizando la marca y componentes
existentes. El home y Entrar conservan su diseño. Evidencia, límites y siguientes
pasos: [avance del dashboard](dashboard-progress.md).

## Unidades de implementación

### 2026-11-13 — Carrusel de «Más que una báscula» (#154)

- El título, las láminas y la navegación comparten una altura mínima de
  una pantalla. En ventanas muy bajas el contenido puede crecer.
- El avance continúa con el puntero encima. El botón pausa y reanuda.
  El foco visible de teclado, una pestaña oculta o menos de 40 % de la
  sección visible detienen el avance. Con movimiento reducido la navegación
  queda manual.
- Chrome comprobado a 375 × 667, 390 × 700, 768 × 768, 1366 × 768 y
  1440 × 900. Se probaron las cuatro láminas en cada tamaño, el intervalo
  real de 7 segundos, el teclado, los gestos táctiles y el acceso por ancla.
  `pnpm lint`, `pnpm test` y `pnpm build` pasan.

### 2026-09-24 — Animación de la gráfica existente

La curva se dibuja progresivamente al entrar en pantalla, seguida de puntos
escalonados, un área tenue y un destello único en el último pesaje.
Duración total aproximada: 2.5 s. No se repite al volver a la sección.
Los 17 datos, la marca inestable y la tabla permanecen sin cambios.
Se usa la API nativa de animaciones; el estado estático mantiene todos los datos
visibles si no hay soporte. Movimiento reducido evita la animación y, si se
activa durante ella, cancela los efectos y muestra el resultado completo.

Verificado con Chrome a 375, 390, 768 y 1440 px: animación en progreso y final,
sin repetición ni desbordamiento; cambio de preferencia de movimiento en vivo.
ESLint y build de Vite correctos; ninguna excepción JavaScript.
Este ajuste anima la gráfica existente; el rediseño completo de Historial
según la lámina 02 continúa pendiente.

### 2026-09-24 — Transición del paisaje de portada

Se aumentó la altura de la franja para suavizar el recorte y se añadió un
fundido inferior al marfil, seguido de espacio antes de Cómo funciona.
El crédito permanece por encima del fundido. En móvil se conserva la foto
oculta, según el diseño existente. Cambio exclusivamente CSS.
Revisión visual a 768 y 1440 px; comprobación de anchos 375, 390, 768 y 1440 px
sin desbordamiento. ESLint y build de Vite correctos.

Cada unidad se revisa y sube por separado a stage.

| Unidad | Alcance | Estado |
|---|---|---|
| 0. Recursos | Inventario, generación, créditos y catálogo de imágenes | Terminada |
| 1. Encabezado y portada | Marca, acceso, H1, acciones, paleta y adaptación móvil | Implementada; revisión visual manual pendiente |
| 2. Vista de ejemplo | Tarjeta de Pesajes, paisaje WebP y rótulos de ejemplo | Integrada; revisión visual manual pendiente |
| 3. Cómo funciona | Tres pasos y ancla como-funciona | Implementada; revisión visual manual pendiente |
| 4. Beneficios | Durante el pesaje y Después de la jornada | Implementada; revisión visual manual pendiente |
| 5. Historial | Fotografía, gráfica y tabla accesible | Pendiente |
| 6. Privacidad y FAQ | Banda de privacidad y acordeón accesible | Implementada y verificada; aceptación visual pendiente |
| 7. Cierre y pie | Acceso final, ayuda, marca y enlaces reales | Implementada y verificada; aceptación visual pendiente |
| 8. Integración | Navegación completa, responsive, accesibilidad y regresiones | Pendiente |

Cómo funciona, Beneficios, Conocer Fierro y Preguntas frecuentes tienen un
destino real. El encabezado y el pie comparten los destinos correspondientes.

## 2026-09-24 — Lámina 03: preguntas y acceso

Implementada por petición del usuario antes de retomar Historial.
Rama: codex/home-preguntas-acceso, desde stage.

- Banda marfil con candado SVG y textos canónicos de privacidad.
- Cuatro preguntas con details/summary, primera abierta; apertura independiente.
- Cierre verde con inicio de sesión y ayuda; pie con marca original y navegación.
- Sustituye las antiguas secciones de privacidad/fotografías y cierre.
- CSS acotado en preguntas-acceso.css; no modifica el diseño del login.

Validación: ESLint y Vite ejecutados directamente desde node_modules, correctos.
Chrome a 375, 390, 768 y 1440 px: teclado Enter/Espacio, clic, varias preguntas
abiertas, foco visible, anclas, controles de al menos 44 px y sin desbordamiento.
Ambos botones nuevos abren el login existente y permiten volver al home.
Movimiento reducido verificado; ninguna excepción JavaScript durante el recorrido.
No se inició sesión con una cuenta ni se validaron pantallas privadas.

[Evidencia y capturas de la etapa 03](design/home/revision-03.md).
Pendiente: aceptación visual del usuario, Historial e integración final del home.

## 2026-09-23 — Portada y vista de ejemplo

Estado: implementadas en cursor/home-section-1-stage-7dff; no declararlas
terminadas hasta completar revisión visual manual.

Resultado:

- Encabezado propio con marca canónica e inicio de sesión visible.
- Hero de dos columnas en escritorio y una columna en móvil.
- Textos canónicos, acción principal, acción secundaria y nota de invitación.
- Vista no interactiva de Pesajes con fixtures estáticos y rótulo visible.
- Paisaje convertido de PNG de 2.8 MB a WebP de aproximadamente 224 KB.
- Enlace Saltar al contenido, focos visibles y controles de al menos 44 px.
- Estilos limitados al home; Shell, login y panel privado no cambian.
- La primera sección antigua fue sustituida por Cómo funciona con lista ordenada,
  tres pasos canónicos y composición responsive.
- Beneficios usa dos imágenes WebP optimizadas, textos canónicos y apilado móvil.
- Las demás secciones antiguas conservan temporalmente su tema.

Validación:

- ESLint directo desde node_modules: pasó.
- Build de Vite directo desde node_modules: pasó.
- La página local está disponible en http://127.0.0.1:5173.
- Revisión visual automatizada bloqueada porque Computer Use no inició.
- Revisión manual a 375, 390, 768 y 1440 px pendiente antes de promover a main.

## 2026-09-23 — Preparación de imágenes

- Tres PNG originales en apps/web/public/img, con entradas en el catálogo.
- Prompts, procedencia, alt y recomendaciones en frontend-home-images.md.
- El paisaje ya tiene un derivado WebP; los otros PNG no se cargarán hasta que
  su unidad produzca derivados optimizados y responsive.

## Siguiente unidad recomendada

### Corrección visual posterior a f72029b

Se corrigieron los iconos de los tres pasos, la fotografía de corral, la
composición del teléfono y la jerarquía móvil. Véase
[revisión de lámina 02](design/home/revision-02.md).
Chrome comprobado a 375, 390, 768 y 1440 px, sin desbordamiento de página,
con fotografía cargada y sin excepciones JavaScript. No equivale a aceptación
visual del usuario ni a completar Historial.

`pnpm lint/build` siguen bloqueados por
`ERR_PNPM_ABORTED_REMOVE_MODULES_DIR_NO_TTY`. ESLint y Vite pasaron ejecutados
desde `apps/web/node_modules`, sin reinstalar dependencias.

Unidad 5: sustituir la sección actual de datos por Historial, con fotografía,
gráfica y tabla accesible según la lámina de referencia correspondiente.

## 2026-10-25 — Propuestas A, B y C del diseño del home

Diseño aprobado: https://claude.ai/artifact/LS3Vcw3zrJK2aaxNZJMCP6 (#88, #89, #90).

- A: lista de espera como acción principal, sellos y vista de ejemplo sobre el paisaje.
- B: fuentes plegadas (una cita las abre), privacidad como pregunta frecuente,
  banda de acceso sustituida por una línea en la lista de espera.
- C: Fierro Vision en desarrollo, una sola foto, estado por capacidad y
  detalles técnicos en un desplegable.

Medido con Playwright sobre `vite preview`: alto en celular (390 px) de 9,856
a 7,521 px; escritorio (1280 px) de 7,517 a 5,979 px. Sin desbordamiento
horizontal. `pnpm lint` y `pnpm build` pasan.
