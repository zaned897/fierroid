import "./mas-que-bascula.css";

/**
 * Lo que sale de los pesajes además del registro (#93, #94). Cada idea dice su
 * estado real, con la misma regla que Fierro Vision: lo que aún no se
 * construye no se presenta como disponible. Las vistas van siempre abiertas
 * porque son lo que vende; son ejemplos fijos, sin consultas a datos de
 * ningún rancho.
 */
const IDEAS = [
  {
    id: "atras",
    titulo: "Animales que se quedan atrás",
    texto: "Al terminar la jornada, quiénes no ganaron peso desde el último pesaje.",
    disponible: false,
    icono: <path d="M3 17l6-6 4 4 8-8" />,
    vista: {
      titulo: "3 animales para revisar",
      filas: [
        ["BEDE50D3", "2 pesajes sin ganar", "−0.2 kg/día", "alerta"],
        ["A41C0977", "Ganancia más baja del lote", "+0.1 kg/día", "alerta"],
        ["7F22B018", "Lectura atípica, no cuenta", "Revisar", "alerta"],
      ],
    },
  },
  {
    id: "venta",
    titulo: "Peso de venta",
    texto: "Tú pones la meta. Fierro cuenta cuántos ya llegaron y cuántos van cerca.",
    disponible: false,
    icono: <><circle cx="12" cy="12" r="9" /><path d="M12 7v5l3 2" /></>,
    vista: {
      titulo: "Meta 480 kg · 6 ya en peso",
      filas: [
        ["BEDE50D3", "437.5 kg · faltan 42.5 kg", "~ 6 semanas"],
        ["C90A1123", "462.0 kg · faltan 18 kg", "~ 3 semanas"],
      ],
      nota: "Estimado con la ganancia diaria de cada animal; cambia si cambia la comida.",
    },
  },
  {
    id: "equipo",
    titulo: "Tu equipo te avisa",
    texto: "El último reporte de cada estación y los pesajes que tiene por enviar.",
    disponible: true,
    icono: <><rect x="4" y="4" width="16" height="12" rx="2" /><path d="M8 20h8" /></>,
    vista: {
      titulo: "Equipos · Los Encinos",
      filas: [
        ["Manga 1", "Último reporte hace 2 min", "0 por enviar"],
        ["Báscula del potrero", "Último reporte ayer, 18:40", "23 por enviar", "alerta"],
      ],
      nota: "Los pesajes siguen guardados en el equipo y se envían cuando vuelve la conexión.",
    },
  },
  {
    id: "comprador",
    titulo: "Lista para el comprador",
    texto: "El lote pesado, arete por arete, listo para compartir.",
    disponible: false,
    icono: <><path d="M6 3h9l3 3v15H6z" /><path d="M9 12h6M9 16h6" /></>,
    vista: {
      titulo: "Lote 3 · 40 animales · 17,480 kg",
      filas: [
        ["BEDE50D3", "07:14 · Manga 1", "437.5 kg"],
        ["C90A1123", "07:16 · Manga 1", "462.0 kg"],
        ["A41C0977", "07:19 · Manga 1", "401.5 kg"],
      ],
      nota: "No es un documento oficial.",
    },
  },
];

function Vista({ vista }) {
  return (
    <figure className="mqb-vista">
      <strong className="mqb-vista-titulo">{vista.titulo}</strong>
      <ul>
        {vista.filas.map(([arete, detalle, valor, tono]) => (
          <li key={arete}>
            <span>{arete}<small>{detalle}</small></span>
            <strong className={tono === "alerta" ? "mqb-alerta" : undefined}>{valor}</strong>
          </li>
        ))}
      </ul>
      {vista.nota && <p className="mqb-vista-nota">{vista.nota}</p>}
      <figcaption>Datos de ejemplo</figcaption>
    </figure>
  );
}

export default function MasQueBascula() {
  return (
    <section className="bloque mas-que-bascula" id="mas-que-bascula" aria-labelledby="mqb-titulo" data-revelar>
      <div className="mqb-cabeza">
        <p className="mqb-ceja">Más que una báscula</p>
        <h2 id="mqb-titulo">Tus pesajes, convertidos en decisiones.</h2>
        <p>Con el arete, el peso y la hora que ya guarda el equipo, Fierro te dice qué revisar, qué vender y si tu equipo sigue reportando.</p>
      </div>
      <ul className="mqb-ideas">
        {IDEAS.map((idea) => (
          <li key={idea.id} className="mqb-idea">
            <div className="mqb-icono" aria-hidden="true">
              <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">{idea.icono}</svg>
            </div>
            <div className="mqb-cuerpo">
              <h3>{idea.titulo}</h3>
              <p>{idea.texto}</p>
              <span className={`mqb-estado ${idea.disponible ? "mqb-disponible" : ""}`}>
                {idea.disponible ? "Disponible" : "Próximamente"}
              </span>
            </div>
            <Vista vista={idea.vista} />
          </li>
        ))}
      </ul>
    </section>
  );
}
