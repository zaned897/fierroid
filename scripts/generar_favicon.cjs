// Rasteriza apps/web/public/favicon.svg a los PNG que piden los navegadores
// que no usan SVG (Safari, iOS, el manifest de Android).
//
//     node scripts/generar_favicon.cjs
//
// Usa el Chromium de Playwright: dibujar curvas con antialias en stdlib no
// compensa para un script que se corre cuando cambia el favicon.
const { readFileSync } = require("node:fs");
const { chromium } = require("playwright");

const DIR = "apps/web/public";
const svg = readFileSync(`${DIR}/favicon.svg`, "utf8");
const ORO = "#c4a35a";

// Disco con esquinas transparentes: pestaña y manifest "any".
const disco = (lado) => `<img src="data:image/svg+xml;base64,${Buffer.from(svg).toString("base64")}" width="${lado}" height="${lado}">`;

// A sangre, sin transparencia: iOS compone sobre negro lo transparente y
// Android recorta los maskable a su forma. La cabeza va dentro de la zona segura,
// subida 4/64 porque en el SVG su centro cae en y=36, no en 32.
const sangre = (lado, escala) => {
  const cabeza = svg.replace(/<circle cx="32" cy="32" r="31"[^>]*\/>/, "");
  const dentro = Math.round(lado * escala);
  return `<div style="width:${lado}px;height:${lado}px;background:${ORO};display:grid;place-items:center">`
    + `<img src="data:image/svg+xml;base64,${Buffer.from(cabeza).toString("base64")}" width="${dentro}" height="${dentro}" style="transform:translateY(-${dentro / 16}px)"></div>`;
};

const salidas = [
  ["favicon-32.png", 32, disco(32)],
  ["icon-192.png", 192, disco(192)],
  ["icon-512.png", 512, disco(512)],
  ["apple-touch-icon.png", 180, sangre(180, 0.86)],
  ["icon-maskable-512.png", 512, sangre(512, 0.72)],
];

(async () => {
const navegador = await chromium.launch();
const pagina = await navegador.newPage();
for (const [nombre, lado, html] of salidas) {
  await pagina.setViewportSize({ width: lado, height: lado });
  await pagina.setContent(`<body style="margin:0;background:transparent">${html}</body>`);
  await pagina.screenshot({ path: `${DIR}/${nombre}`, omitBackground: true, clip: { x: 0, y: 0, width: lado, height: lado } });
  console.log(`  ${DIR}/${nombre}`);
}
await navegador.close();
})();
