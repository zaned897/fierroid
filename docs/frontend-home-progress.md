# Relevo del frontend del home

## Unidades de implementación

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
