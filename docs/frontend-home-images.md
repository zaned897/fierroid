# Imágenes del home

Fecha: 2026-09-23. Alcance: recursos preparados, sin cambios en la página visible.
Referencia funcional: [frontend-home.md](frontend-home.md).

## Inventario y selección

| Sección | Recurso | Decisión |
|---|---|---|
| Portada | `home-paisaje-ia` | Nuevo paisaje horizontal. El hero anterior es un retrato cercano, menos adecuado para la franja panorámica. |
| Durante el pesaje | `home-corral-ia` | Nueva escena de manejo. La foto de corral existente es histórica; la de arete representa su colocación, no su lectura. |
| Después de la jornada | `home-consulta-ia` | Nueva escena de consulta del celular, ausente del catálogo anterior. |
| Historial del animal | `home-hero` | Reutilizar el brahman existente. Mantener su procedencia CC0 y no atribuirle datos reales de la aplicación. |
| Vista de Pesajes | HTML/CSS con fixtures | Construir según la especificación; no rasterizar texto y controles. |
| Tres pasos, privacidad, FAQ | Iconos existentes / SVG | No necesitan fotografías ni generación adicional. |
| Marca | Marca.jsx | Conservar la marca original. |
| Gráfica | GraficaPeso.jsx | Reutilizar con identificación de ejemplo y alternativa accesible. |

## Archivos nuevos

- [Paisaje](../apps/web/public/img/home-paisaje-ia.png).
- [Manejo en corral](../apps/web/public/img/home-corral-ia.png).
- [Consulta del celular](../apps/web/public/img/home-consulta-ia.png).

Los tres originales son PNG de 1536 × 1024. Se registraron en el catálogo
`apps/web/src/img/index.js`, con dimensiones y texto alternativo. Ninguna imagen
previa fue reemplazada. La herramienta utilizada fue `image_gen`, modo integrado,
sin CLI ni API externa configurada. Los prompts exactos están en
[image-prompts.json](design/home/image-prompts.json).

## Integración

- Usar las claves del catálogo en lugar de rutas personales de generación.
- Son escenas ilustrativas generadas por IA, no fotos de clientes, pruebas de
  hardware ni evidencia de una instalación. No presentarlas como testimonios.
- Mantener un pie discreto «Imagen ilustrativa generada con IA» al integrarlas.
  `Foto.jsx` no lo agrega automáticamente: resolver ese pie dentro de la sección,
  sin confundirlo con una licencia CC de los recursos anteriores.
- Hero: paisaje opcional, subordinado al producto. Como decoración redundante,
  usar alt vacío. Como imagen informativa, usar el alt del catálogo.
- Beneficios: proporción inicial 3:2; probar 4:3 en móvil con `object-fit: cover`.
  Mantener persona y animal reconocibles; no recortar automáticamente en cuadrado.
- Para una franja muy panorámica del paisaje, ajustar `object-position` hacia
  abajo y revisar el recorte para no cortar las cabezas de los animales.
- El teléfono no muestra una UI inventada y no escanea al animal. La imagen del
  corral no demuestra que exista una báscula compatible o un lector instalado.
- Los PNG son originales de trabajo (aproximadamente 1.9–2.8 MB cada uno).
  Antes de cargarlos en el home público, producir derivados WebP/AVIF y tamaños
  responsive, comprobar el resultado visual y actualizar catálogo y créditos.
  No cargar los tres PNG originales a un celular con señal limitada.
- Declarar dimensiones, diferir imágenes bajo la portada y conservar atribuciones
  cuando se usen fotografías anteriores con CC BY.

## Verificación y pendientes

### Revisión visual de la lámina 02

`home-corral-v2-ia.webp` (1448 × 1086) sustituye el encuadre lejano en
Beneficios y se reutiliza en el fondo de los pasos. El recurso se generó con
la herramienta integrada image_gen; su prompt completo está en
`design/home/corral-v2-prompt.md`. Los originales anteriores se conservan.
La segunda tarjeta ahora usa `TelefonoConsulta.jsx`, una vista HTML estática
con fondo de paisaje ilustrativo, en lugar de la foto de consulta lejana.
Ambas tarjetas mantienen la proporción 4:3 y la procedencia visible.

Se inspeccionaron visualmente las tres salidas: composición, anatomía general,
ausencia de texto/marcas añadidas y pertinencia con la sección. No se realizó
revisión responsive en navegador porque la página no fue modificada.
Quedan pendientes compresión, recortes finales y montaje dentro del frontend.
