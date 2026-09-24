import HomeIcon from "./icons/HomeIcon.jsx";

const PASOS = [
  {
    titulo: "Identifica al animal",
    texto: "El lector reconoce su arete.",
    icono: "arete",
  },
  {
    titulo: "Guarda el pesaje",
    texto: "El equipo registra el peso en el corral.",
    icono: "bascula",
  },
  {
    titulo: "Consulta su historial",
    texto: "Los datos se sincronizan cuando hay conexión.",
    icono: "nube",
  },
];

export default function Diagrama() {
  return (
    <div className="diagrama diagrama-home">
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
