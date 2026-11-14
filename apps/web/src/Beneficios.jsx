import Foto from "./Foto.jsx";

export default function Beneficios() {
  return (
    <section className="home-beneficios home-manga" id="beneficios" aria-labelledby="beneficios-titulo" data-revelar>
      <Foto nombre="home-corral-v2-ia" className="home-manga-foto" pie="Imagen ilustrativa generada con IA" />
      <div className="home-manga-contenido">
        <h2 id="beneficios-titulo">Arete y peso, juntos</h2>
        <ol className="home-manga-anotaciones" aria-label="Lo que guarda Fierro">
          <li>Un registro por pesaje</li>
          <li>Historial en el celular</li>
        </ol>
      </div>
    </section>
  );
}
