import { useId } from "react";

import HomeIcon from "./icons/HomeIcon.jsx";

const PASOS = [
  {
    titulo: "Arete",
    texto: "Lectura automática",
    icono: "arete",
  },
  {
    titulo: "Pesaje local",
    texto: "Guarda sin señal",
    icono: "bascula",
  },
  {
    titulo: "Historial",
    texto: "Sube con conexión",
    icono: "nube",
  },
];

export default function Diagrama() {
  const idDescripcion = useId();

  return (
    <div className="diagrama diagrama-home">
      <p id={idDescripcion} className="home-solo-lectores">
        El lector identifica el arete; el equipo guarda el peso en el corral,
        incluso sin señal. Los datos se sincronizan cuando hay conexión.
      </p>
      <ol className="pasos" aria-describedby={idDescripcion}>
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
