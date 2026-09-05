/**
 * Índice único de imágenes estáticas del producto.
 *
 * Los componentes no escriben rutas: importan de aquí. Sustituir una imagen
 * (por ejemplo, cuando llegue la fotografía propia) es editar su entrada,
 * no buscar la ruta por todo el repo.
 *
 * Cada entrada trae medidas reales del archivo para declararlas en el `<img>`
 * y que el layout no salte mientras carga, más el crédito completo: cuando la
 * licencia lo pide (CC BY), la atribución debe verse en la página, no solo en
 * CREDITOS.md. Los archivos viven en `public/img/` y su trazabilidad en
 * `public/img/CREDITOS.md`.
 */

export const imagenes = {
  "home-hero": {
    src: "/img/home-hero.webp",
    width: 1600,
    height: 1067,
    alt: "Ganado brahman descansando a la sombra de un árbol",
    autor: "Bernard Gagnon",
    licencia: "CC0 1.0",
    fuente: "https://commons.wikimedia.org/w/index.php?curid=146759986",
    requiereAtribucion: false,
  },
  "seccion-corral": {
    src: "/img/seccion-corral.webp",
    width: 804,
    height: 626,
    alt: "Ganado reunido en el corral esperando pesaje",
    autor: "Russell Lee (Library of Congress)",
    licencia: "Public domain",
    fuente: "https://commons.wikimedia.org/w/index.php?curid=31267700",
    requiereAtribucion: false,
  },
  "seccion-manga": {
    src: "/img/seccion-manga.webp",
    width: 800,
    height: 576,
    alt: "Ganado en la manga de manejo durante el trabajo de rancho",
    autor: "Sadie_Girl",
    licencia: "CC BY 2.0",
    fuente: "https://commons.wikimedia.org/w/index.php?curid=40214455",
    requiereAtribucion: true,
  },
  "seccion-arete": {
    src: "/img/seccion-arete.webp",
    width: 1060,
    height: 707,
    alt: "Colocación del arete a un animal en la manga",
    autor: "Loren Kerns",
    licencia: "CC BY 2.0",
    fuente: "https://commons.wikimedia.org/w/index.php?curid=87440060",
    requiereAtribucion: true,
  },
  "seccion-hato": {
    src: "/img/seccion-hato.webp",
    width: 1200,
    height: 874,
    alt: "Vaquero a caballo reuniendo el hato en el campo",
    autor: "dany13",
    licencia: "CC BY 2.0",
    fuente: "https://commons.wikimedia.org/w/index.php?curid=129817085",
    requiereAtribucion: true,
  },
  "animal-sin-foto": {
    src: "/img/animal-sin-foto.webp",
    width: 640,
    height: 500,
    alt: "Silueta de animal, sin fotografía registrada",
    autor: "Ryan Kissinger, NIAID (NIH BioArt)",
    licencia: "Public domain",
    fuente: "https://commons.wikimedia.org/w/index.php?curid=178924310",
    requiereAtribucion: false,
  },
};
