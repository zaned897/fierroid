import Marca from "./Marca.jsx";
import "./preguntas-acceso.css";

const PREGUNTAS = [
  {
    pregunta: "¿Qué pasa si se va la señal?",
    respuesta: "El equipo guarda los pesajes localmente y los envía cuando recupera la conexión. Para ver nuevos datos en tu celular necesitas conexión.",
  },
  {
    pregunta: "¿Cómo entro a Fierro?",
    respuesta: "El acceso es por invitación. Pide al administrador de tu rancho que dé de alta tu correo y después selecciona Iniciar sesión.",
  },
  {
    pregunta: "¿Qué información puedo consultar?",
    respuesta: "Puedes consultar los pesajes y la información de los animales a los que tu cuenta tiene acceso.",
  },
  {
    pregunta: "¿Qué equipo necesita mi rancho?",
    respuesta: "Fierro conecta un lector de aretes y una báscula con un equipo que registra los pesajes. La compatibilidad depende de los modelos y debe verificarse antes de instalarlos.",
  },
];

export default function PreguntasAcceso({ onEntrar }) {
  return (
    <div className="home-preguntas-acceso">
      <section className="home-privacidad" aria-labelledby="privacidad-titulo">
        <div className="home-privacidad-contenido">
          <svg className="home-privacidad-icono" viewBox="0 0 32 40" aria-hidden="true" focusable="false">
            <path d="M8 17V11a8 8 0 0 1 16 0v6" fill="none" stroke="currentColor" strokeWidth="4" />
            <rect x="2" y="15" width="28" height="23" rx="4" fill="currentColor" />
            <circle cx="16" cy="25" r="3" fill="#f7f8f3" />
            <path d="M16 26v5" stroke="#f7f8f3" strokeWidth="3" strokeLinecap="round" />
          </svg>
          <div>
            <h2 id="privacidad-titulo">La información de tu rancho, para tu equipo.</h2>
            <p>Cada usuario ve únicamente la información que le corresponde.</p>
          </div>
        </div>
      </section>

      <section className="home-faq" id="preguntas-frecuentes" aria-labelledby="faq-titulo">
        <div className="home-acceso-contenido">
          <h2 id="faq-titulo">Preguntas frecuentes</h2>
          <div className="home-faq-lista">
            {PREGUNTAS.map(({ pregunta, respuesta }, indice) => (
              <details className="home-faq-item" key={pregunta} open={indice === 0}>
                <summary>
                  <span>{pregunta}</span>
                  <span className="home-faq-signo" aria-hidden="true" />
                </summary>
                <p>{respuesta}</p>
              </details>
            ))}
          </div>
        </div>
      </section>

      <section className="home-acceso-final" aria-labelledby="acceso-final-titulo">
        <div className="home-acceso-contenido home-acceso-columnas">
          <div>
            <h2 id="acceso-final-titulo">¿Tu rancho ya usa Fierro?</h2>
            <p>Inicia sesión con tu correo autorizado.</p>
          </div>
          <div className="home-acceso-accion">
            <button type="button" className="home-entrar" onClick={onEntrar}>Iniciar sesión</button>
            <p>Si aún no tienes acceso, pide al administrador de tu rancho que dé de alta tu correo.</p>
          </div>
        </div>
      </section>
    </div>
  );
}

export function PieHome({ onEntrar }) {
  return (
    <footer className="home-pie">
      <div className="home-pie-contenido">
        <a className="home-pie-marca" href="/" aria-label="Fierro, inicio">
          <Marca size={48} />
          <span><strong>FIERRO</strong><span>Del corral a tu bolsillo.</span></span>
        </a>
        <nav aria-label="Navegación al pie">
          <a href="#como-funciona">Cómo funciona</a>
          <a href="#preguntas-frecuentes">Preguntas frecuentes</a>
          <button type="button" onClick={onEntrar}>Iniciar sesión</button>
        </nav>
      </div>
    </footer>
  );
}
