# Relevo del frontend del home

## Unidades de implementación

Cada unidad se revisa y sube por separado a stage.

| Unidad | Alcance | Estado |
|---|---|---|
| 0. Recursos | Inventario, generación, créditos y catálogo de imágenes | Terminada |
| 1. Encabezado y portada | Marca, acceso, H1, acciones, paleta y adaptación móvil | Implementada; revisión visual manual pendiente |
| 2. Vista de ejemplo | Tarjeta de Pesajes, paisaje WebP y rótulos de ejemplo | Integrada; revisión visual manual pendiente |
| 3. Cómo funciona | Tres pasos y ancla como-funciona | Implementada; revisión visual manual pendiente |
| 4. Beneficios | Durante el pesaje y Después de la jornada | Pendiente |
| 5. Historial | Fotografía, gráfica y tabla accesible | Pendiente |
| 6. Privacidad y FAQ | Banda de privacidad y acordeón accesible | Pendiente |
| 7. Cierre y pie | Acceso final, ayuda, marca y enlaces reales | Pendiente |
| 8. Integración | Navegación completa, responsive, accesibilidad y regresiones | Pendiente |

No publicar enlaces a unidades inexistentes. Por ahora solo Cómo funciona y
Conocer Fierro tienen un destino real. Beneficios y FAQ se añadirán con sus
secciones, no como anclas vacías.

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

Unidad 3: sustituir la sección actual por Cómo funciona con los tres pasos
canónicos, lista ordenada y adaptación móvil.
