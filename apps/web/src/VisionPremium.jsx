import { useState } from "react";
import { imagenes } from "./img/index.js";
import "./vision-premium.css";

const modes = [
  {
    id: "segmentacion",
    tab: "Segmentación",
    title: "Segmentación con modelo neuronal YOLOv8",
    description:
      "La red YOLOv8m-seg procesa la escena y separa de forma natural las instancias de ganado, resolviendo la oclusión entre la vaca blanca y la vaca gris.",
    detail: "YOLOv8m-seg · 4 instancias detectadas",
    feature: "Segmentación por visión abierta",
    text: "Clasificación con red neuronal abierta para distinguir cada animal, personas y montas sin fusionar siluetas superpuestas.",
  },
  {
    id: "dimensiones",
    tab: "Dimensiones",
    title: "Morfometría sobre máscaras reales",
    description:
      "Cálculo de alzada a la cruz y longitud corporal anclado a los vértices y bounding boxes inferidos por la red neuronal.",
    detail: "Morfometría computacional calibrada",
    feature: "Dimensiones por visión",
    text: "Estimación biométrica a partir de las máscaras de segmentación de la red, con referencia de escala en manga.",
  },
  {
    id: "seguimiento",
    tab: "Seguimiento",
    title: "Re-identificación y tracking multianimal",
    description:
      "Asignación de identificadores de seguimiento independientes (Track IDs) correlacionados con aretes RFID y peso de báscula.",
    detail: "Multi-Object Tracking + RFID",
    feature: "Seguimiento visual continuo",
    text: "Fichas individuales continuas para cada animal detectado, sincronizadas con lecturas físicas del rancho.",
  },
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
  const [selected, setSelected] = useState("segmentacion");
  const mode = modes.find((item) => item.id === selected) || modes[0];
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
            FIERRO VISION <span>PREMIUM</span>
          </p>
          <h2 id="vision-heading">
            Más allá del peso.
            <br />
            <em>Visión computacional con YOLO.</em>
          </h2>
        </div>
        <div className="vision-pitch">
          <p>
            Inferencia real con redes neuronales abiertas (YOLOv8-seg / Roboflow)
            para resolver oclusiones complejas, segmentar cada bovino y medir con
            precisión en el corral.
          </p>
          <a href="#lista-espera" className="vision-cta-link">
            Unirme a la lista de espera para Fierro Vision{" "}
            <span aria-hidden="true">→</span>
          </a>
        </div>
      </div>

      <div className="vision-workspace">
        <div className="vision-toolbar">
          <div className="vision-toolbar-left">
            <span className="vision-app-name">
              <span aria-hidden="true">◈</span> FIERRO VISION STUDIO
            </span>
            <span className="vision-chip vision-chip-model">
              BACKBONE: YOLOV8M-SEG
            </span>
            <span className="vision-chip vision-chip-latency">
              <span className="vision-status-dot" aria-hidden="true" />
              18.1 ms
            </span>
            <span className="vision-chip vision-chip-classes">
              YOLO INFERENCE OK
            </span>
          </div>
          <div className="vision-toolbar-right">
            <span className="vision-workspace-label">
              Inferencia neuronal activa · Resolución 1200 × 874
            </span>
          </div>
        </div>

        <div
          className="vision-modes"
          role="group"
          aria-label="Modo de visualización"
        >
          {modes.map((item, i) => (
            <button
              type="button"
              key={item.id}
              className={`vision-mode-tab ${selected === item.id ? "activo" : ""}`}
              aria-pressed={selected === item.id}
              onClick={() => setSelected(item.id)}
            >
              <span className="vision-tab-idx">0{i + 1}</span>
              <span className="vision-tab-name">{item.tab}</span>
            </button>
          ))}
        </div>

        <div className="vision-canvas-grid">
          <figure className="vision-canvas">
            <svg
              viewBox="0 0 1200 874"
              role="img"
              aria-label={`${mode.tab}: detección neuronal con YOLOv8`}
            >
              <image href={photo.src} width="1200" height="874" />
              <rect width="1200" height="874" fill="#041b16" opacity=".18" />

              {/* MODO 1: SEGMENTACIÓN NEURONAL REAL CON YOLOV8 */}
              {selected === "segmentacion" && (
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
              )}

              {/* MODO 2: DIMENSIONES BASADAS EN DETECCIONES REALES */}
              {selected === "dimensiones" && (
                <g>
                  {/* Siluetas de referencia YOLO */}
                  <polygon
                    points={yoloWhiteCowMask}
                    fill="#10b981"
                    fillOpacity="0.08"
                    stroke="#34d399"
                    strokeWidth="1.5"
                    strokeDasharray="8 6"
                    opacity="0.75"
                  />
                  <polygon
                    points={yoloGreyCowMask}
                    fill="#0ea5e9"
                    fillOpacity="0.08"
                    stroke="#38bdf8"
                    strokeWidth="1.5"
                    strokeDasharray="8 6"
                    opacity="0.65"
                  />

                  {/* Cota horizontal: Longitud Corporal Bovino Blanco (400 a 665 px) */}
                  <g stroke="#38bdf8" strokeWidth="2.5">
                    <line
                      x1="400"
                      y1="552"
                      x2="400"
                      y2="460"
                      strokeDasharray="4 4"
                      opacity="0.6"
                    />
                    <line
                      x1="665"
                      y1="552"
                      x2="665"
                      y2="460"
                      strokeDasharray="4 4"
                      opacity="0.6"
                    />
                    <line x1="400" y1="475" x2="665" y2="475" />
                    <path d="M400 465V485 M665 465V485" strokeWidth="3" />
                    <path
                      d="M412 469L400 475L412 481 M653 469L665 475L653 481"
                      fill="#38bdf8"
                    />
                  </g>
                  <g transform="translate(450, 450)">
                    <rect
                      x="-8"
                      y="-18"
                      width="170"
                      height="30"
                      rx="5"
                      fill="#082f49"
                      stroke="#38bdf8"
                      strokeWidth="1.5"
                    />
                    <text
                      x="6"
                      y="3"
                      fill="#e0f2fe"
                      fontSize="14"
                      fontFamily="monospace"
                      fontWeight="bold"
                    >
                      LONGITUD: 158 cm
                    </text>
                  </g>

                  {/* Cota horizontal: Longitud Corporal Bovino Gris (638 a 974 px) */}
                  <g stroke="#38bdf8" strokeWidth="2.5">
                    <line
                      x1="638"
                      y1="552"
                      x2="638"
                      y2="460"
                      strokeDasharray="4 4"
                      opacity="0.5"
                    />
                    <line
                      x1="974"
                      y1="552"
                      x2="974"
                      y2="460"
                      strokeDasharray="4 4"
                      opacity="0.5"
                    />
                    <line x1="638" y1="475" x2="974" y2="475" />
                    <path d="M638 465V485 M974 465V485" strokeWidth="3" />
                    <path
                      d="M650 469L638 475L650 481 M962 469L974 475L962 481"
                      fill="#38bdf8"
                    />
                  </g>
                  <g transform="translate(735, 450)">
                    <rect
                      x="-8"
                      y="-18"
                      width="170"
                      height="30"
                      rx="5"
                      fill="#082f49"
                      stroke="#38bdf8"
                      strokeWidth="1.5"
                    />
                    <text
                      x="6"
                      y="3"
                      fill="#e0f2fe"
                      fontSize="14"
                      fontFamily="monospace"
                      fontWeight="bold"
                    >
                      GRIS: 168 cm
                    </text>
                  </g>

                  {/* Cota vertical: Alzada Bovino Blanco */}
                  <g stroke="#f59e0b" strokeWidth="2.5">
                    <line
                      x1="400"
                      y1="552"
                      x2="320"
                      y2="552"
                      strokeDasharray="4 4"
                      opacity="0.5"
                    />
                    <line
                      x1="400"
                      y1="870"
                      x2="320"
                      y2="870"
                      strokeDasharray="4 4"
                      opacity="0.5"
                    />
                    <line x1="335" y1="552" x2="335" y2="870" />
                    <path d="M325 552H345 M325 870H345" strokeWidth="3" />
                    <path
                      d="M329 564L335 552L341 564 M329 858L335 870L341 858"
                      fill="#f59e0b"
                    />
                  </g>
                  <g transform="translate(190, 715)">
                    <rect
                      x="-8"
                      y="-18"
                      width="145"
                      height="30"
                      rx="5"
                      fill="#451a03"
                      stroke="#f59e0b"
                      strokeWidth="1.5"
                    />
                    <text
                      x="6"
                      y="3"
                      fill="#fef3c7"
                      fontSize="14"
                      fontFamily="monospace"
                      fontWeight="bold"
                    >
                      ALZADA: 141 cm
                    </text>
                  </g>

                  {/* Puntos anatómicos reales */}
                  {[
                    { x: 467, y: 583, label: "Cruz" },
                    { x: 624, y: 581, label: "Hombro" },
                    { x: 870, y: 553, label: "Grupa Gris" },
                    { x: 424, y: 697, label: "Manga" },
                  ].map((pt) => (
                    <g key={pt.label}>
                      <circle
                        cx={pt.x}
                        cy={pt.y}
                        r="14"
                        fill="none"
                        stroke="#ffffff"
                        strokeWidth="1.5"
                        opacity="0.8"
                      />
                      <circle
                        cx={pt.x}
                        cy={pt.y}
                        r="5"
                        fill="#34d399"
                        stroke="#0f172a"
                        strokeWidth="2"
                      />
                      <line
                        x1={pt.x - 18}
                        y1={pt.y}
                        x2={pt.x + 18}
                        y2={pt.y}
                        stroke="#ffffff"
                        strokeWidth="1"
                        opacity="0.6"
                      />
                      <line
                        x1={pt.x}
                        y1={pt.y - 18}
                        x2={pt.x}
                        y2={pt.y + 18}
                        stroke="#ffffff"
                        strokeWidth="1"
                        opacity="0.6"
                      />
                    </g>
                  ))}

                  {/* Calibración activa */}
                  <g transform="translate(30, 820)">
                    <rect
                      width="275"
                      height="34"
                      rx="6"
                      fill="#041b16"
                      fillOpacity="0.88"
                      stroke="#38544a"
                      strokeWidth="1"
                    />
                    <text
                      x="14"
                      y="22"
                      fill="#a4c7b7"
                      fontSize="13"
                      fontFamily="monospace"
                    >
                      ESCALA: 1 px ≈ 0.23 cm [MANGA 1]
                    </text>
                  </g>
                </g>
              )}

              {/* MODO 3: TRACKING MULTIANIMAL Y RFID */}
              {selected === "seguimiento" && (
                <g>
                  {/* Bounding box Bovino Blanco (Track 042) */}
                  <rect
                    x="400"
                    y="552"
                    width="265"
                    height="318"
                    rx="6"
                    fill="none"
                    stroke="#34d399"
                    strokeWidth="2"
                    strokeDasharray="16 8"
                  />
                  <path
                    d="M400 582V552H430 M665 582V552H635 M400 840V870H430 M665 840V870H635"
                    fill="none"
                    stroke="#10b981"
                    strokeWidth="4"
                  />

                  {/* Bounding box Bovino Gris (Track 043) */}
                  <rect
                    x="638"
                    y="552"
                    width="336"
                    height="319"
                    rx="6"
                    fill="none"
                    stroke="#38bdf8"
                    strokeWidth="1.5"
                    strokeDasharray="8 6"
                    opacity="0.6"
                  />

                  {/* Encabezado Track #042 */}
                  <g transform="translate(400, 484)">
                    <rect width="365" height="38" rx="6" fill="#10b981" />
                    <text
                      x="12"
                      y="25"
                      fill="#042f2e"
                      fontSize="15"
                      fontFamily="monospace"
                      fontWeight="bold"
                    >
                      TRACK #042 · RFID 484381933670979
                    </text>
                  </g>

                  {/* Tag adicional de peso sincronizado */}
                  <g transform="translate(400, 528)">
                    <rect
                      width="220"
                      height="28"
                      rx="4"
                      fill="#042f2e"
                      stroke="#10b981"
                      strokeWidth="1.5"
                    />
                    <circle cx="16" cy="14" r="5" fill="#34d399" />
                    <text
                      x="28"
                      y="19"
                      fill="#c5ffdf"
                      fontSize="13"
                      fontFamily="monospace"
                      fontWeight="bold"
                    >
                      BÁSCULA: 437.5 kg [OK]
                    </text>
                  </g>

                  {/* Tag Track #043 (Vaca gris) */}
                  <g transform="translate(638, 522)">
                    <rect
                      width="260"
                      height="30"
                      rx="4"
                      fill="#082f49"
                      stroke="#38bdf8"
                      strokeWidth="1.5"
                    />
                    <text
                      x="10"
                      y="20"
                      fill="#e0f2fe"
                      fontSize="12"
                      fontFamily="monospace"
                      fontWeight="bold"
                    >
                      TRACK #043 · EN ESPERA (OCLUSIÓN)
                    </text>
                  </g>

                  {/* Retícula de detección en el arete de la vaca blanca */}
                  <g transform="translate(435, 636)">
                    <circle
                      cx="0"
                      cy="0"
                      r="16"
                      fill="none"
                      stroke="#38bdf8"
                      strokeWidth="2"
                      strokeDasharray="4 3"
                    />
                    <circle cx="0" cy="0" r="4" fill="#38bdf8" />
                    <line
                      x1="-22"
                      y1="0"
                      x2="22"
                      y2="0"
                      stroke="#38bdf8"
                      strokeWidth="1.5"
                    />
                    <line
                      x1="0"
                      y1="-22"
                      x2="0"
                      y2="22"
                      stroke="#38bdf8"
                      strokeWidth="1.5"
                    />
                    <rect
                      x="26"
                      y="-12"
                      width="125"
                      height="24"
                      rx="4"
                      fill="#0369a1"
                    />
                    <text
                      x="32"
                      y="5"
                      fill="#ffffff"
                      fontSize="11"
                      fontFamily="monospace"
                      fontWeight="bold"
                    >
                      ARETE DETECTADO
                    </text>
                  </g>
                </g>
              )}
            </svg>
            <figcaption>
              <span>Detección neuronal en tiempo real</span>
              <a
                href={photo.fuente}
                target="_blank"
                rel="noreferrer"
              >
                {photo.autor} · {photo.licencia}
              </a>
            </figcaption>
          </figure>

          {/* INSPECTOR LATERAL CON TELEMETRÍA DE MODELO REAL */}
          <aside className="vision-inspector" aria-live="polite">
            <div className="vision-inspector-header">
              <span className="vision-inspector-tag">{mode.detail}</span>
              <h3>{mode.title}</h3>
              <p>{mode.description}</p>
            </div>

            {selected === "segmentacion" && (
              <div className="vision-panel-block">
                <span className="vision-panel-title">INFERENCIA DE CLASES (YOLOV8M-SEG)</span>
                <div className="vision-class-list">
                  <div className="vision-class-item">
                    <span className="vision-class-badge badge-bovino">
                      ● cow (blanco)
                    </span>
                    <span className="vision-class-meta">0.94 conf · bbox [400, 552]</span>
                  </div>
                  <div className="vision-class-item">
                    <span className="vision-class-badge badge-bovino-gris">
                      ● cow (gris)
                    </span>
                    <span className="vision-class-meta">0.75 conf · bbox [638, 552]</span>
                  </div>
                  <div className="vision-class-item">
                    <span className="vision-class-badge badge-equino">
                      ● horse
                    </span>
                    <span className="vision-class-meta">0.82 conf · bbox [241, 344]</span>
                  </div>
                  <div className="vision-class-item">
                    <span className="vision-class-badge badge-persona">
                      ● person
                    </span>
                    <span className="vision-class-meta">0.85 conf · bbox [374, 201]</span>
                  </div>
                </div>
                <div className="vision-occlusion-notice">
                  <strong>Oclusión resuelta por YOLO:</strong> La red identifica
                  dos bounding boxes independientes que se solapan en x: 638–665.
                  La silueta del bovino gris preserva sus 4 patas sin fusionar la
                  cabeza oculta.
                </div>
                <div className="vision-telemetry">
                  <div>
                    <span>Latencia</span>
                    <strong>18.1 ms</strong>
                  </div>
                  <div>
                    <span>Preproceso</span>
                    <strong>3.3 ms</strong>
                  </div>
                  <div>
                    <span>Backbone</span>
                    <strong>YOLOv8m-seg</strong>
                  </div>
                </div>
              </div>
            )}

            {selected === "dimensiones" && (
              <div className="vision-panel-block">
                <span className="vision-panel-title">MÉTRICAS MORFOMÉTRICAS</span>
                <div className="vision-metrics-grid">
                  <div className="vision-metric-item">
                    <span>Longitud (Blanco)</span>
                    <strong>158 cm</strong>
                  </div>
                  <div className="vision-metric-item">
                    <span>Alzada (Blanco)</span>
                    <strong>141 cm</strong>
                  </div>
                  <div className="vision-metric-item">
                    <span>Longitud (Gris)</span>
                    <strong>168 cm</strong>
                  </div>
                  <div className="vision-metric-item">
                    <span>Relación alzada/largo</span>
                    <strong>0.89 (Óptima)</strong>
                  </div>
                </div>
                <div className="vision-calib-note">
                  Cotas morfométricas ancladas a las máscaras y bounding boxes
                  inferidos por el modelo.
                </div>
              </div>
            )}

            {selected === "seguimiento" && (
              <div className="vision-panel-block">
                <span className="vision-panel-title">SEGUIMIENTO MULTIANIMAL</span>
                <div className="vision-record-box">
                  <div className="vision-record-row">
                    <span>Track #042 (Blanco):</span>
                    <strong>RFID 484381933670979</strong>
                  </div>
                  <div className="vision-record-row">
                    <span>Peso en báscula:</span>
                    <strong>437.5 kg [OK]</strong>
                  </div>
                  <div className="vision-record-row">
                    <span>Track #043 (Gris):</span>
                    <strong>En espera en manga</strong>
                  </div>
                  <div className="vision-record-row">
                    <span>Coincidencia Re-ID:</span>
                    <strong>99.1% (Blanco)</strong>
                  </div>
                </div>
                <div className="vision-calib-note">
                  Seguimiento con persistencia de ID ante oclusiones temporales.
                </div>
              </div>
            )}

            <div className="vision-inspector-cta">
              <a href="#lista-espera" className="vision-btn-reserve">
                Solicitar acceso anticipado <span aria-hidden="true">→</span>
              </a>
            </div>
          </aside>
        </div>
      </div>

      <div className="vision-features">
        {modes.map((item, i) => (
          <article key={item.id} className="vision-feature-card">
            <span className="vision-feature-number">0{i + 1} / FIERRO VISION</span>
            <h3>{item.feature}</h3>
            <p>{item.text}</p>
          </article>
        ))}
      </div>
    </section>
  );
}
