import Foto from "./Foto.jsx";

const BENEFICIOS = [
  {
    titulo: "Durante el pesaje",
    texto: "Relaciona el animal con su peso en un solo registro.",
    imagen: "home-corral-ia",
  },
  {
    titulo: "Después de la jornada",
    texto: "Consulta los pesajes y el historial de cada animal.",
    imagen: "home-consulta-ia",
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
        <div className="home-beneficios-grid">
          {BENEFICIOS.map((beneficio) => (
            <article className="home-beneficio" key={beneficio.titulo}>
              <Foto
                nombre={beneficio.imagen}
                className="home-beneficio-foto"
                pie="Imagen ilustrativa generada con IA"
              />
              <div className="home-beneficio-texto">
                <h3>{beneficio.titulo}</h3>
                <p>{beneficio.texto}</p>
              </div>
            </article>
          ))}
        </div>
      </div>
    </section>
  );
}
