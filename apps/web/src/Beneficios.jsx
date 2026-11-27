import Foto from "./Foto.jsx";
import TelefonoConsulta from "./TelefonoConsulta.jsx";

const BENEFICIOS = [
  {
    titulo: "Animal + peso",
    texto: "Relaciona el animal con su peso en un solo registro.",
    imagen: "home-corral-v2-ia",
  },
  {
    titulo: "Historial",
    texto: "Consulta los pesajes y el historial de cada animal.",
    telefono: true,
  },
];

export default function Beneficios() {
  return (
    <section
      className="bloque home-beneficios"
      id="beneficios"
      aria-labelledby="beneficios-titulo"
      data-revelar
    >
      <div className="home-beneficios-contenido">
        <h2 id="beneficios-titulo">En el corral y desde tu celular</h2>
        {/* Una figura grande por beneficio, no una rejilla de tarjetas (#158).
            La figura va antes que el texto en el DOM y también en pantalla. */}
        <div className="home-beneficios-filas">
          {BENEFICIOS.map((beneficio, indice) => (
            <article className="home-beneficio" key={beneficio.titulo}>
              {beneficio.telefono ? <TelefonoConsulta /> : <Foto
                nombre={beneficio.imagen}
                className="home-beneficio-foto"
              />}
              <div className="home-beneficio-texto">
                <span className="home-beneficio-num" aria-hidden="true">
                  {String(indice + 1).padStart(2, "0")}
                </span>
                <h3>{beneficio.titulo}</h3>
                <p className="home-solo-lectores">{beneficio.texto}</p>
              </div>
            </article>
          ))}
        </div>
      </div>
    </section>
  );
}
