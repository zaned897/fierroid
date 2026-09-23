const PASOS = [
  {
    titulo: "Identifica al animal",
    texto: "El lector reconoce su arete.",
    icono: "RFID",
  },
  {
    titulo: "Guarda el pesaje",
    texto: "El equipo registra el peso en el corral.",
    icono: "kg",
  },
  {
    titulo: "Consulta su historial",
    texto: "Los datos se sincronizan cuando hay conexión.",
    icono: "↗",
  },
];

export default function Diagrama() {
  return (
    <div className="diagrama diagrama-home">
      <ol className="pasos">
        {PASOS.map((paso, indice) => (
          <li key={paso.titulo} className="paso">
            <div className="paso-cabecera">
              <span className="paso-icono" aria-hidden="true">
                {paso.icono}
              </span>
              <span className="paso-num">0{indice + 1}</span>
            </div>
            <h3>{paso.titulo}</h3>
            <p>{paso.texto}</p>
          </li>
        ))}
      </ol>
    </div>
  );
}
