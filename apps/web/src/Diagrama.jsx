import HomeIcon from "./icons/HomeIcon.jsx";

const PASOS = [
  {
    titulo: "Arete",
    texto: "Lector",
    icono: "arete",
  },
  {
    titulo: "Pesaje local",
    texto: "Sin señal",
    icono: "bascula",
  },
  {
    titulo: "Historial",
    texto: "Con conexión.",
    icono: "nube",
  },
];

export default function Diagrama() {
  return (
    <div className="diagrama diagrama-home" aria-describedby="flujo-descripcion">
      <p id="flujo-descripcion" className="home-solo-lectores">
        El lector identifica el arete; el equipo guarda el peso en el corral,
        incluso sin señal. Los datos se sincronizan cuando hay conexión.
      </p>
      <ol className="pasos">
        {PASOS.map((paso, indice) => (
          <li key={paso.titulo} className="paso">
            <div className="paso-senal" aria-hidden="true">
              <span className="paso-num">{indice + 1}</span>
              <span className="paso-icono"><HomeIcon tipo={paso.icono} /></span>
            </div>
            <div className="paso-texto">
              <h3>{paso.titulo}</h3>
              <p>{paso.texto}</p>
            </div>
          </li>
        ))}
      </ol>
    </div>
  );
}
