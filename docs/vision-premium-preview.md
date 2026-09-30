# Fierro Vision: maqueta premium local

2026-09-29. El usuario pidió presentar visión computacional como funciones premium
con estética de plataforma de visión, sin rótulos de ejemplo ni imagen ilustrativa
en el home. Esta petición reemplaza esas restricciones visuales de la guía anterior
para esta maqueta local. No se publica con esta entrega.

Implementación: sección interactiva con modos Segmentación, Dimensiones y
Seguimiento, foto existente CC BY 2.0 y superposiciones basadas en inferencia
real de modelo abierto de segmentación YOLOv8 (YOLOv8m-seg / Roboflow exportable).
El modelo resolvió la escena identificando independientemente al bovino blanco en primer
plano (`conf 0.94`), al bovino gris detrás (`conf 0.75`), al caballo (`conf 0.82`) y al vaquero (`conf 0.85`),
descartando la clasificación unificada falsa y resolviendo la oclusión entre ambos animales.
El crédito fotográfico se conserva. No hay servicio premium en producción habilitado.
CTA a lista de espera existente. Backend, hardware y autenticación sin cambios.

Archivos: VisionPremium.jsx, vision-premium.css, Secciones.jsx, docs/design/yolo_masks.json
y eliminación de rótulos visibles en Home, Beneficios, VistaPesajesDemo, TelefonoConsulta, GraficaPeso y Login.
Mantener la procedencia de los recursos en CREDITOS.md.
Build (`vite build`), linter (`eslint`) y suite de pruebas (`pytest`, `ruff`) verificados localmente en verde.
