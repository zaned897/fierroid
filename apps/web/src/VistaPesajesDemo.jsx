import { CowIcon } from "./icons/cows.jsx";

const lecturas = [
  { peso: "437.5 kg", hora: "19:42" },
  { peso: "279.0 kg", hora: "19:27" },
  { peso: "31.0 kg", hora: "19:26" },
  { peso: "325.0 kg", hora: "19:26" },
];

export default function VistaPesajesDemo() {
  return (
    <figure className="home-demo" aria-labelledby="home-demo-caption">
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
          <section className="home-demo-ultimo" aria-label="Último pesaje de ejemplo">
            <div>
              <span className="home-demo-etiqueta">Último pesaje</span>
              <strong>437.5 kg</strong>
              <span className="home-demo-animal">
                <CowIcon variant="perfil" size={18} />
                Animal BEDE50D3
              </span>
            </div>
            <time>Hoy, 19:42</time>
          </section>
          <div className="home-demo-recientes">
            <h3>Lecturas recientes</h3>
            <div className="home-demo-tabla" role="table" aria-label="Lecturas recientes de ejemplo">
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
      <figcaption id="home-demo-caption">Vista de ejemplo</figcaption>
    </figure>
  );
}
