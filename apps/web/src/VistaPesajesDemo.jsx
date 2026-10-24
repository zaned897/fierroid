import { useEffect, useState } from "react";

import { CowIcon } from "./icons/cows.jsx";

const lecturas = [
  { peso: "437.5 kg", hora: "19:42" },
  { peso: "279.0 kg", hora: "19:27" },
  { peso: "31.0 kg", hora: "19:26" },
  { peso: "325.0 kg", hora: "19:26" },
];

/**
 * Lo que la báscula muestra mientras el animal se acomoda: oscila y converge.
 * Es ilustrativo, pero cuenta lo real: Fierro guarda la lectura cuando se
 * estabiliza, no la primera cifra que aparece.
 */
const OSCILACION = [412.8, 452.1, 428.6, 443.9, 433.2, 439.7, 436.4, 437.9, 437.5];
const PASO_MS = 170;

/**
 * Con movimiento reducido arranca ya estable: se ve 437.5 kg quieto. Si no,
 * recorre la oscilación una sola vez y siempre termina en el mismo valor.
 */
function useLecturaEstabilizada() {
  const final = OSCILACION.length - 1;
  const [indice, setIndice] = useState(() =>
    window.matchMedia("(prefers-reduced-motion: reduce)").matches ? final : 0,
  );

  useEffect(() => {
    if (indice >= final) return undefined;
    const reloj = setTimeout(() => setIndice(indice + 1), PASO_MS);
    return () => clearTimeout(reloj);
  }, [indice, final]);

  return { kg: OSCILACION[indice], estable: indice === final };
}

export default function VistaPesajesDemo() {
  const { kg, estable } = useLecturaEstabilizada();

  return (
    <figure className={`home-demo ${estable ? "guardado" : "midiendo"}`} aria-label="Panel de pesajes">
      <div className="home-demo-marco">
        <aside className="home-demo-lateral" aria-hidden="true">
          <span className="home-demo-marca">Fierro</span>
          <span className="home-demo-activo">Pesajes</span>
          <span>Animales</span>
          <span>Estaciones</span>
        </aside>
        <div className="home-demo-panel">
          <div className="home-demo-barra" aria-hidden="true">
            <span>Los Encinos</span>
            <span>Juan Pérez</span>
          </div>
          <h2>Pesajes</h2>
          <section className="home-demo-ultimo" aria-label="Último pesaje">
            <div>
              <span className="home-demo-etiqueta">Último pesaje</span>
              {/* Quien usa lector de pantalla escucha solo el valor guardado. */}
              <strong aria-hidden="true">{kg.toFixed(1)} kg</strong>
              <span className="home-demo-sr">437.5 kg</span>
              <span className="home-demo-estado" aria-hidden="true">{estable ? "Estable · guardado" : "Estabilizando…"}</span>
              <span className="home-demo-animal">
                <CowIcon variant="perfil" size={18} />
                Animal BEDE50D3
              </span>
            </div>
            <time>Hoy, 19:42</time>
          </section>
          <div className="home-demo-recientes">
            <h3>Lecturas recientes</h3>
            <div className="home-demo-tabla" role="table" aria-label="Lecturas recientes">
              <div className="home-demo-fila home-demo-cabecera" role="row">
                <span role="columnheader">Animal</span>
                <span role="columnheader">Peso</span>
                <span role="columnheader">Hora</span>
              </div>
              {lecturas.map((lectura) => (
                <div className="home-demo-fila" role="row" key={lectura.peso}>
                  <span role="cell" className="home-demo-animal">
                    <CowIcon variant="perfil" size={15} />
                    BEDE50D3
                  </span>
                  <span role="cell">{lectura.peso}</span>
                  <span role="cell">{lectura.hora}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </figure>
  );
}

