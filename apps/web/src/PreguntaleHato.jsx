import "./preguntale-hato.css";

/**
 * Bloque estático del home (#111). Muestra dos intercambios de ejemplo
 * escritos a mano, sin llamar a la API ni a ningún modelo.
 */
const INTERCAMBIOS = [
  {
    id: "problemas",
    pregunta: "¿Qué vaca tiene problemas?",
    chips: ["Revisé 42 animales", "184 pesajes"],
    introduccion: "Hay 2 animales para revisar:",
    puntos: [
      "BEDE50D3 lleva 2 pesajes seguidos sin ganar peso (−0.2 kg/día).",
      "A41C0977 tiene la ganancia diaria más baja del lote (+0.1 kg/día).",
    ],
    nota: "Conté pesajes estables, sin pruebas ni lecturas atípicas.",
  },
  {
    id: "peso-total",
    pregunta: "¿Cuál es el peso total hasta hoy?",
    chips: ["Revisé 42 animales", "184 pesajes"],
    introduccion: "El peso total es de 17,486 kg en 41 animales.",
    puntos: [],
    nota: "Suma del último pesaje estable de cada animal; 1 quedó fuera por tener su último pesaje atípico.",
  },
];

export default function PreguntaleHato() {
  return (
    <section
      className="preguntale-hato"
      id="preguntale-hato"
      aria-labelledby="preguntale-hato-titulo"
      data-revelar
    >
      <div className="preguntale-hato-cabeza">
        <div>
          <p className="preguntale-hato-ceja">
            Pregúntale a tu hato <span>Premium · Próximamente</span>
          </p>
          <h2 id="preguntale-hato-titulo">
            Pregúntale a Fierro como le preguntarías a tu vaquero.
          </h2>
        </div>
        <div className="preguntale-hato-pitch">
          <p>
            Escribe tu duda y recibe la respuesta con los números exactos de tus
            pesajes, diciendo siempre qué animales entraron en la cuenta y cuáles
            quedaron fuera.
          </p>
        </div>
      </div>

      <div className="preguntale-hato-marco">
        <div className="preguntale-hato-conversacion">
          <p className="preguntale-hato-etiqueta">Conversación de ejemplo</p>
          <ol className="preguntale-hato-hilo" aria-label="Conversación de ejemplo">
            {INTERCAMBIOS.map((item) => (
              <li key={item.id} className="preguntale-hato-par">
                <div className="preguntale-hato-usuario">
                  <p>{item.pregunta}</p>
                </div>
                <div className="preguntale-hato-respuesta">
                  <div className="preguntale-hato-chips">
                    {item.chips.map((chip) => (
                      <span key={chip} className="preguntale-hato-chip">
                        {chip}
                      </span>
                    ))}
                  </div>
                  <p className="preguntale-hato-intro">{item.introduccion}</p>
                  {item.puntos.length > 0 && (
                    <ul className="preguntale-hato-lista">
                      {item.puntos.map((punto) => (
                        <li key={punto}>{punto}</li>
                      ))}
                    </ul>
                  )}
                  <p className="preguntale-hato-nota">{item.nota}</p>
                </div>
              </li>
            ))}
          </ol>
        </div>

        <aside className="preguntale-hato-lateral">
          <ul className="preguntale-hato-reglas">
            <li>
              <strong>Cuentas claras</strong>
              <span>Cada cifra sale de los pesajes registrados en tu rancho, sin estimaciones.</span>
            </li>
            <li>
              <strong>Aretes a un toque</strong>
              <span>Toca cualquier arete en la respuesta para abrir su ficha e historial.</span>
            </li>
            <li>
              <strong>Sin ocultar datos dudosos</strong>
              <span>Las lecturas inestables o atípicas se avisan aparte para no inflar el total.</span>
            </li>
          </ul>

          <a href="#lista-espera" className="vision-btn-reserve preguntale-hato-cta">
            Avísame cuando esté listo <span aria-hidden="true">→</span>
          </a>
        </aside>
      </div>
    </section>
  );
}
