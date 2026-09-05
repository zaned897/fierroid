# Créditos de imágenes

Trazabilidad de cada archivo en `apps/web/public/img/`. Licencia verificada por
imagen (metadatos `extmetadata` de Wikimedia Commons), no por el sitio de
origen. Descarga del 2026-09-05.

Son imágenes de licencia libre de uso temporal: la expectativa es sustituirlas
por fotografía propia de Fierro. Sustituir una es editar su entrada en
[`apps/web/src/img/index.js`](../../src/img/index.js) y borrar el archivo —
esta tabla debe actualizarse en el mismo cambio.

| Archivo | Fuente | URL original | Autor | Licencia | Fecha de descarga |
|---|---|---|---|---|---|
| `home-hero.webp` | Wikimedia Commons | https://commons.wikimedia.org/w/index.php?curid=146759986 | Bernard Gagnon | CC0 1.0 | 2026-09-05 |
| `seccion-corral.webp` | Wikimedia Commons (Library of Congress) | https://commons.wikimedia.org/w/index.php?curid=31267700 | Russell Lee | Public domain | 2026-09-05 |
| `seccion-manga.webp` | Wikimedia Commons (Flickr) | https://commons.wikimedia.org/w/index.php?curid=40214455 | Sadie_Girl | CC BY 2.0 | 2026-09-05 |
| `seccion-arete.webp` | Wikimedia Commons (Flickr) | https://commons.wikimedia.org/w/index.php?curid=87440060 | Loren Kerns | CC BY 2.0 | 2026-09-05 |
| `seccion-hato.webp` | Wikimedia Commons (Flickr) | https://commons.wikimedia.org/w/index.php?curid=129817085 | dany13 | CC BY 2.0 | 2026-09-05 |
| `animal-sin-foto.webp` | Wikimedia Commons (NIH BioArt) | https://commons.wikimedia.org/w/index.php?curid=178924310 | Ryan Kissinger, NIAID | Public domain | 2026-09-05 |

## Notas por archivo

- **home-hero.webp** — Brahman cattle in Costa Rica.jpg (4051×2701, 2023-01-30).
  Convertida a WebP 1600×1067. CC0: sin atribución obligatoria.
- **seccion-corral.webp** — Cattle in corral waiting to be weighed before being
  trailed to railroad, 1a35023v.jpg (1024×805, septiembre 1942, FSA/Office of
  War Information vía Library of Congress). Recortada para quitar el marco de
  la diapositiva; WebP 804×626. Dominio público.
- **seccion-manga.webp** — Squeeze chute (5988549063).jpg (800×576, 2011-07-29,
  Flickr, https://creativecommons.org/licenses/by/2.0). Reconvertida a WebP sin
  recorte. **CC BY 2.0 exige atribución visible en la página.**
- **seccion-arete.webp** — Ear tagging with a cattle crush 2 (7277371954).jpg
  (3872×2592, 2012-05-26, Flickr, https://creativecommons.org/licenses/by/2.0).
  Recortada (quedó 1060×707) para descartar residuos fuera de escena;
  **CC BY 2.0 exige atribución visible en la página.**
- **seccion-hato.webp** — DSC00234 Brasil Pantanal Cowboys Herding Zebu Cattle
  on Miranda (15522881708).jpg (3292×2398, 2013-09-11, Flickr,
  https://creativecommons.org/licenses/by/2.0). Reconvertida a WebP 1200×874.
  **CC BY 2.0 exige atribución visible en la página.**
- **animal-sin-foto.webp** — Dairy Cow Silhouette (NIH BioArt 100 - 628685).png
  (1608×1258, 2024-09-26, cortesía de NIAID, dominio público como obra del
  gobierno federal de EE. UU.). Conserva canal alfa; WebP 640×500.

## Atribución visible (pendiente de integración)

Tres imágenes son CC BY 2.0 (`requiereAtribucion: true` en el índice). Su
crédito completo está aquí y en el índice, y debe renderizarse junto a la
imagen cuando los componentes las integren (ticket #36). Las CC0 y dominio
público no la exigen.

## Prohibido

- Agregar imágenes sin su fila en esta tabla y su entrada en el índice.
- Descargar de resultados de búsqueda de imágenes (licencia no verificable).
- Licencias NC, ND o ShareAlike: el producto es comercial y las derivadas
  (WebP, recortes) complican el cumplimiento.
