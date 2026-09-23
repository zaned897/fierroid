# Relevo del frontend del home

## Unidades correctas de implementación

Cada unidad se revisa y sube por separado a `stage`.

| Unidad | Alcance | Estado |
|---|---|---|
| 0. Recursos | Inventario, generación, créditos y catálogo de imágenes | Terminada |
| 1. Encabezado y portada | Marca, acceso visible, H1, descripción, paleta local y adaptación móvil | Implementada; revisión visual manual pendiente |
| 2. Vista de ejemplo | Tarjeta de Pesajes con fixtures estáticos y rótulo «Vista de ejemplo» | Pendiente |
| 3. Cómo funciona | Tres pasos y ancla `#como-funciona` | Pendiente |
| 4. Beneficios | «Durante el pesaje» y «Después de la jornada» con imágenes optimizadas | Pendiente |
| 5. Historial | Fotografía, gráfica, tabla accesible y rótulo de ejemplo | Pendiente |
| 6. Privacidad y FAQ | Banda de privacidad y acordeón accesible | Pendiente |
| 7. Cierre y pie | Acceso final, ayuda, marca y enlaces reales | Pendiente |
| 8. Integración | Navegación completa, responsive, accesibilidad y regresiones | Pendiente |

No añadir enlaces de navegación a una unidad todavía inexistente. El botón
`Conocer Fierro` y las anclas secundarias se incorporan cuando sus destinos
reales lleguen a `stage`; no se publican enlaces rotos ni secciones vacías.

## 2026-09-23 — Unidad 1: encabezado y portada

Estado: implementada en `cursor/home-section-1-stage-7dff`; no declararla
terminada hasta completar revisión visual manual.

Resultado:

- Encabezado propio del home con marca canónica e inicio de sesión visible.
- Portada con textos canónicos, verde bosque, marfil y azul petróleo.
- Enlace «Saltar al contenido», focos visibles y controles de al menos 44 px.
- Estilos limitados a `.home-publica`; `Shell.jsx`, login y panel privado no cambian.
- Las secciones antiguas conservan temporalmente su tema oscuro y siguen debajo.
- La vista ilustrativa, la fotografía y «Conocer Fierro» quedan para las unidades
  que proporcionan sus contenidos y destinos reales.

Validación:

- ESLint directo desde `node_modules`: pasó.
- Build de Vite directo desde `node_modules`: pasó.
- `pnpm lint` y `pnpm build`: no ejecutados porque pnpm intentó reinstalar
  módulos y abortó con `ERR_PNPM_ABORTED_REMOVE_MODULES_DIR_NO_TTY`.
- Revisión visual automatizada: bloqueada porque el navegador de Computer Use no
  inició (`registered Core setup has not completed`).
- Revisión manual a 375, 390, 768 y 1440 px: pendiente antes de promover a main.

## 2026-09-23 — Unidad 0: preparación de imágenes

Estado: recursos generados y revisados; integración visual pendiente.

- Tres PNG en `apps/web/public/img`, con entradas en el catálogo.
- Imágenes anteriores conservadas; el brahman existente puede reutilizarse.
- Prompts, procedencia, alt y recomendaciones en `frontend-home-images.md`.
- Los PNG de trabajo no deben cargarse en el home: primero producir WebP/AVIF y
  tamaños responsive para la unidad que realmente use cada imagen.

## Siguiente unidad recomendada

Unidad 2: vista de ejemplo de Pesajes con fixtures estáticos, sin consultas a
`stage` ni producción. Mantenerla no interactiva y claramente rotulada.
