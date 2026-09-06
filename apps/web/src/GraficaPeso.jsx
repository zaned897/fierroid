import { useId, useState } from "react";

/**
 * La curva de peso de un animal real.
 *
 * Los 17 puntos salen de la base de stage, del arete 484381933670979: un
 * becerro que pasó de 43 a 106.5 kg entre mayo y septiembre de 2026. Son datos
 * sembrados, no de un cliente, y por eso la sección los llama ejemplo. Lo que
 * no son es inventados.
 *
 * La lectura del 27 de agosto llegó marcada inestable, y se dibuja distinta a
 * propósito: es el principio del sistema —falla ruidosa, nunca datos falsos—
 * en una imagen. Se distingue por **forma y etiqueta**, no por color: el
 * validador de paleta da ΔE 4.1 en deuteranopía entre el oro de la serie y el
 * terracota del aviso, así que el color no puede ser la única pista.
 */
const SERIE = [
  { fecha: "2026-05-14", kg: 43.0 },
  { fecha: "2026-05-21", kg: 45.0 },
  { fecha: "2026-05-28", kg: 50.0 },
  { fecha: "2026-06-04", kg: 56.0 },
  { fecha: "2026-06-11", kg: 55.5 },
  { fecha: "2026-06-18", kg: 60.0 },
  { fecha: "2026-06-25", kg: 65.0 },
  { fecha: "2026-07-02", kg: 69.0 },
  { fecha: "2026-07-09", kg: 73.0 },
  { fecha: "2026-07-16", kg: 76.0 },
  { fecha: "2026-07-23", kg: 77.0 },
  { fecha: "2026-07-30", kg: 84.0 },
  { fecha: "2026-08-06", kg: 89.0 },
  { fecha: "2026-08-13", kg: 93.0 },
  { fecha: "2026-08-20", kg: 99.0 },
  { fecha: "2026-08-27", kg: 101.0, inestable: true },
  { fecha: "2026-09-03", kg: 106.5 },
];

const ANCHO = 640;
const ALTO = 260;
const MARGEN = { arriba: 24, derecha: 24, abajo: 34, izquierda: 44 };

const TRAZO = {
  x0: MARGEN.izquierda,
  x1: ANCHO - MARGEN.derecha,
  y0: MARGEN.arriba,
  y1: ALTO - MARGEN.abajo,
};

const MIN_KG = 30;
const MAX_KG = 120;
const MARCAS_Y = [30, 60, 90, 120];

const posX = (i) => TRAZO.x0 + (i / (SERIE.length - 1)) * (TRAZO.x1 - TRAZO.x0);
const posY = (kg) => TRAZO.y1 - ((kg - MIN_KG) / (MAX_KG - MIN_KG)) * (TRAZO.y1 - TRAZO.y0);

const mes = (fecha) =>
  new Date(`${fecha}T12:00:00`).toLocaleDateString("es-MX", { month: "short" });

export default function GraficaPeso() {
  const [activo, setActivo] = useState(null);
  const idTabla = useId();
  const punto = activo === null ? null : SERIE[activo];

  const linea = SERIE.map((d, i) => `${i ? "L" : "M"}${posX(i)} ${posY(d.kg)}`).join(" ");

  return (
    <figure className="grafica">
      <figcaption className="grafica-titulo">
        Peso del arete <span className="tag">484381933670979</span>, mayo a
        septiembre de 2026
        <span className="grafica-nota">Ejemplo con datos de nuestro entorno de pruebas.</span>
      </figcaption>

      <svg
        viewBox={`0 0 ${ANCHO} ${ALTO}`}
        className="grafica-svg"
        role="img"
        aria-describedby={idTabla}
        aria-label="Curva de peso: de 43 a 106.5 kilogramos en 17 pesajes; uno marcado inestable"
      >
        {/* Rejilla recesiva: orienta y no compite con la serie. */}
        {MARCAS_Y.map((kg) => (
          <g key={kg}>
            <line
              x1={TRAZO.x0}
              x2={TRAZO.x1}
              y1={posY(kg)}
              y2={posY(kg)}
              className="grafica-rejilla"
            />
            <text x={TRAZO.x0 - 10} y={posY(kg) + 4} className="grafica-eje" textAnchor="end">
              {kg}
            </text>
          </g>
        ))}

        {[0, 4, 8, 12, 16].map((i) => (
          <text key={i} x={posX(i)} y={ALTO - 12} className="grafica-eje" textAnchor="middle">
            {mes(SERIE[i].fecha)}
          </text>
        ))}

        <path d={linea} className="grafica-linea" />

        {SERIE.map((d, i) => (
          <g key={d.fecha}>
            {/* El area sensible es mayor que la marca: apuntar a 8px con el
                dedo, o con guantes, no funciona. */}
            <circle
              cx={posX(i)}
              cy={posY(d.kg)}
              r={16}
              className="grafica-blanco"
              onMouseEnter={() => setActivo(i)}
              onMouseLeave={() => setActivo(null)}
            />
            <circle
              cx={posX(i)}
              cy={posY(d.kg)}
              r={d.inestable ? 6 : 4}
              className={d.inestable ? "grafica-punto inestable" : "grafica-punto"}
            />
          </g>
        ))}

        {/* Etiquetas directas solo donde dicen algo: el principio, el final y
            el dato que el sistema marcó dudoso. Una cifra en cada punto seria
            ruido. */}
        <text x={posX(0)} y={posY(SERIE[0].kg) - 14} className="grafica-valor" textAnchor="start">
          43 kg
        </text>
        <text
          x={posX(SERIE.length - 1)}
          y={posY(SERIE.at(-1).kg) - 14}
          className="grafica-valor"
          textAnchor="end"
        >
          106.5 kg
        </text>
        <text x={posX(15)} y={posY(101) + 26} className="grafica-aviso" textAnchor="middle">
          ⚠ inestable
        </text>

        {punto && (
          <g className="grafica-globo" pointerEvents="none">
            <line
              x1={posX(activo)}
              x2={posX(activo)}
              y1={TRAZO.y0}
              y2={TRAZO.y1}
              className="grafica-cruz"
            />
            <text
              x={Math.min(Math.max(posX(activo), TRAZO.x0 + 40), TRAZO.x1 - 40)}
              y={TRAZO.y0 - 6}
              className="grafica-valor"
              textAnchor="middle"
            >
              {punto.fecha} · {punto.kg} kg{punto.inestable ? " · inestable" : ""}
            </text>
          </g>
        )}
      </svg>

      {/* La tabla no es un extra: es como se lee esto sin ver la gráfica. */}
      <details className="grafica-tabla">
        <summary>Ver los 17 pesajes como tabla</summary>
        <table id={idTabla}>
          <caption>Peso registrado por fecha</caption>
          <thead>
            <tr>
              <th scope="col">Fecha</th>
              <th scope="col">Peso</th>
              <th scope="col">Lectura</th>
            </tr>
          </thead>
          <tbody>
            {SERIE.map((d) => (
              <tr key={d.fecha}>
                <th scope="row">{d.fecha}</th>
                <td>{d.kg} kg</td>
                <td>{d.inestable ? "inestable" : "estable"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </details>
    </figure>
  );
}
