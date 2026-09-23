# Relevo del frontend del home

## 2026-09-23 — Preparación de imágenes

Unidad: inventario, generación y registro de tres imágenes para el home.
Estado: recursos generados y revisados; integración visual pendiente.

- Tres PNG nuevos en apps/web/public/img, con entradas en el catálogo.
- Imágenes anteriores conservadas; brahman existente reutilizable para historial.
- Prompts, procedencia, alt y recomendaciones en frontend-home-images.md.
- No se modificó ninguna pantalla ni se publicó un despliegue.
- Revisión visual de originales completada; pruebas responsive pendientes del montaje.
- pnpm lint y pnpm build no pudieron iniciar: pnpm intentó reinstalar módulos y
  abortó con ERR_PNPM_ABORTED_REMOVE_MODULES_DIR_NO_TTY. No se autorizó su borrado.

Siguiente unidad: optimizar recursos para web y luego continuar el contenedor y
los tokens del home conforme a frontend-home.md. No cargar los PNG originales
sin derivados optimizados. Mantener las imágenes identificadas como ilustrativas.

Validación alternativa: ESLint y Vite ejecutados directamente desde node_modules; ambos pasaron. Formato del diff verificado.
