import { imagenes } from "./img/index.js";
import "./vision-premium.css";

/**
 * Qué puede hacer Fierro Vision hoy. Cada capacidad dice su estado real:
 * lo que aún no se valida no se presenta como resultado (#77, #78).
 */
const CAPACIDADES = [
  { texto: "Separar a cada animal en la foto, aunque estén amontonados", estado: "En prueba", probado: true },
  { texto: "Estimar medidas del cuerpo", estado: "Por validar", probado: false },
  { texto: "Seguir a cada animal entre una pasada y la siguiente", estado: "Por validar", probado: false },
];

const DETECCIONES = [
  { clase: "Vaca blanca", modelo: "cow", confianza: "0.94", insignia: "badge-bovino" },
  { clase: "Vaca gris", modelo: "cow", confianza: "0.75", insignia: "badge-bovino-gris" },
  { clase: "Caballo", modelo: "horse", confianza: "0.82", insignia: "badge-equino" },
  { clase: "Persona", modelo: "person", confianza: "0.85", insignia: "badge-persona" },
];

// Máscaras de segmentación reales extraídas de YOLOv8m-seg
const yoloWhiteCowMask =
  "467,808 452,810 450,827 452,862 457,853 463,831 482,797 487,812 493,842 499,864 516,859 527,842 542,825 561,823 574,834 579,853 626,866 634,847 639,795 645,778 652,763 658,746 664,724 658,673 652,651 647,632 641,602 624,581 611,576 598,568 579,555 555,559 540,564 510,570 495,576 467,583 448,604 409,609 409,621 424,628 437,636 441,656 435,669 429,686 424,697 431,724 444,729 450,748 456,759 461,771 474,789";

const yoloGreyCowMask =
  "870,553 857,559 844,564 827,570 814,576 799,581 776,587 741,592 705,587 667,589 645,594 643,632 651,647 656,662 662,696 664,786 669,810 656,825 671,855 696,870 720,862 726,857 759,868 763,823 757,801 756,767 778,757 789,791 795,817 801,844 814,789 819,772 847,761 864,774 872,787 877,806 876,864 900,849 906,834 911,819 917,806 924,836 930,857 945,861 951,838 960,802 951,757 952,684 958,649 952,598 932,576 915,564";

const yoloHorseMask =
  "422,639 418,639 358,506 531,418 546,437 559,454 566,474 581,499 600,487 615,463 641,480 677,486 692,442 684,407 677,392 669,371 662,354 647,358 621,362 602,381 585,388 568,396 540,405 394,424 362,424 339,435 354,448 373,437 401,426 341,489 324,476 306,474 289,482 274,489 255,512 247,540 244,630 251,669 262,705 274,686 270,643 294,579 309,572 330,562 347,548 354,532 656,581 694,566 671,551 645,581";

const yoloPersonMask =
  "437,202 429,214 426,221 420,231 416,238 412,246 416,268 409,281 394,300 388,309 384,319 381,334 377,349 377,397 381,405 399,418 409,422 424,427 433,431 448,435 459,429 472,424 480,429 476,442 476,450 499,476 502,484 506,491 523,491 557,486 546,469 538,461 529,452 510,437 510,429 514,411 510,397 502,390 493,382 484,369 478,360 474,351 471,304 467,292 474,270 480,257 484,238 493,232 497,227 491,221 482,217";

export default function VisionPremium() {
  const photo = imagenes["seccion-hato"];

  return (
    <section
      className="vision-premium"
      id="fierro-vision"
      aria-labelledby="vision-heading"
      data-revelar
    >
      <div className="vision-heading">
        <div>
          <p className="vision-eyebrow">
            FIERRO VISION <span>EN DESARROLLO</span>
          </p>
          <h2 id="vision-heading">Una cámara en la manga que reconoce a cada animal.</h2>
        </div>
        <div className="vision-pitch">
          <p>
            Estamos probando visión por computadora para separar a cada animal en
            la foto aunque estén amontonados. Se suma a la báscula; no la reemplaza.
          </p>
        </div>
      </div>

      <div className="vision-canvas-grid">
        <figure className="vision-canvas">
          <svg
            viewBox="0 0 1200 874"
            role="img"
            aria-label="Foto de prueba con cada animal y la persona marcados por separado"
          >
            <image href={photo.src} width="1200" height="874" />
            <rect width="1200" height="874" fill="#041b16" opacity=".18" />
              <g strokeLinejoin="round">
                {/* DETECCIÓN 1: PERSONA / VAQUERO (conf 0.85) */}
                <polygon
                  points={yoloPersonMask}
                  fill="#f59e0b"
                  fillOpacity=".32"
                  stroke="#fbbf24"
                  strokeWidth="2"
                />
                <rect
                  x="374"
                  y="201"
                  width="191"
                  height="301"
                  fill="none"
                  stroke="#fbbf24"
                  strokeWidth="1.5"
                  strokeDasharray="4 3"
                  opacity="0.8"
                />
                <g transform="translate(374, 175)">
                  <rect width="118" height="26" rx="4" fill="#f59e0b" />
                  <text
                    x="8"
                    y="18"
                    fill="#0f172a"
                    fontSize="13"
                    fontFamily="monospace"
                    fontWeight="bold"
                  >
                    persona · 0.85
                  </text>
                </g>

                {/* DETECCIÓN 2: EQUINO (conf 0.82) */}
                <polygon
                  points={yoloHorseMask}
                  fill="#8b5cf6"
                  fillOpacity=".35"
                  stroke="#c4b5fd"
                  strokeWidth="2.5"
                />
                <rect
                  x="241"
                  y="344"
                  width="460"
                  height="374"
                  fill="none"
                  stroke="#c4b5fd"
                  strokeWidth="1.5"
                  strokeDasharray="6 4"
                  opacity="0.8"
                />
                <g transform="translate(241, 318)">
                  <rect width="118" height="26" rx="4" fill="#7c3aed" />
                  <text
                    x="8"
                    y="18"
                    fill="#ffffff"
                    fontSize="13"
                    fontFamily="monospace"
                    fontWeight="bold"
                  >
                    equino · 0.82
                  </text>
                </g>

                {/* DETECCIÓN 4: BOVINO GRIS (conf 0.75 - Oclusión resuelta) */}
                <polygon
                  points={yoloGreyCowMask}
                  fill="#0ea5e9"
                  fillOpacity=".38"
                  stroke="#38bdf8"
                  strokeWidth="3"
                />
                <rect
                  x="638"
                  y="552"
                  width="336"
                  height="319"
                  fill="none"
                  stroke="#38bdf8"
                  strokeWidth="1.5"
                  strokeDasharray="6 4"
                  opacity="0.8"
                />
                <path
                  d="M638 582V552H668 M974 582V552H944 M638 841V871H668 M974 841V871H944"
                  fill="none"
                  stroke="#0284c7"
                  strokeWidth="3.5"
                />
                <g transform="translate(638, 524)">
                  <rect width="215" height="28" rx="4" fill="#0284c7" />
                  <text
                    x="8"
                    y="19"
                    fill="#ffffff"
                    fontSize="13"
                    fontFamily="monospace"
                    fontWeight="bold"
                  >
                    bovino [gris] · 0.75
                  </text>
                </g>

                {/* DETECCIÓN 0: BOVINO BLANCO EN PRIMER PLANO (conf 0.94) */}
                <polygon
                  points={yoloWhiteCowMask}
                  fill="#10b981"
                  fillOpacity=".40"
                  stroke="#6ee7b7"
                  strokeWidth="3.5"
                />
                <rect
                  x="400"
                  y="552"
                  width="265"
                  height="318"
                  fill="none"
                  stroke="#34d399"
                  strokeWidth="1.5"
                  strokeDasharray="6 4"
                  opacity="0.8"
                />
                <path
                  d="M400 582V552H430 M665 582V552H635 M400 840V870H430 M665 840V870H635"
                  fill="none"
                  stroke="#10b981"
                  strokeWidth="3.5"
                />
                <g transform="translate(400, 524)">
                  <rect width="220" height="28" rx="4" fill="#10b981" />
                  <text
                    x="10"
                    y="19"
                    fill="#042f2e"
                    fontSize="13"
                    fontFamily="monospace"
                    fontWeight="bold"
                  >
                    bovino [blanco] · 0.94
                  </text>
                </g>
              </g>
          </svg>
          <figcaption>
            <span>Ejemplo sobre una foto de prueba</span>
            <a href={photo.fuente} target="_blank" rel="noreferrer">
              {photo.autor} · {photo.licencia}
            </a>
          </figcaption>
        </figure>

        <aside className="vision-inspector">
          <ul className="vision-capacidades">
            {CAPACIDADES.map((capacidad) => (
              <li key={capacidad.texto}>
                <span>{capacidad.texto}</span>
                <em className={capacidad.probado ? "en-prueba" : "por-validar"}>
                  {capacidad.estado}
                </em>
              </li>
            ))}
          </ul>

          <details className="vision-detalles">
            <summary>Detalles técnicos</summary>
            <p>
              Segmentación con YOLOv8m-seg, un modelo abierto. En esta foto separa
              la vaca gris aunque la blanca le tapa la cabeza.
            </p>
            <ul className="vision-class-list">
              {DETECCIONES.map((deteccion) => (
                <li className="vision-class-item" key={deteccion.clase}>
                  <span className={`vision-class-badge ${deteccion.insignia}`}>
                    {deteccion.clase}
                  </span>
                  <span className="vision-class-meta">
                    {deteccion.modelo} · confianza {deteccion.confianza}
                  </span>
                </li>
              ))}
            </ul>
          </details>

          <a href="#lista-espera" className="vision-btn-reserve">
            Avísame cuando esté listo <span aria-hidden="true">→</span>
          </a>
        </aside>
      </div>
    </section>
  );
}
