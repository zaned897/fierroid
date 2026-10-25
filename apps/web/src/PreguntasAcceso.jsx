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
    pregunta: "¿Quién ve la información de mi rancho?",
    respuesta: "Tu equipo. Cada usuario ve únicamente la información que le corresponde.",
  },
  {
    pregunta: "¿Por qué una lectura aparece como inestable?",
    respuesta: "Porque la báscula no se estabilizó mientras el animal se movía. La lectura se guarda igual y queda marcada, para que decidas si repetir el pesaje. Nunca se corrige ni se oculta.",
  },
  {
    pregunta: "¿Qué aretes puede leer?",
    respuesta: "Fierro está pensado para aretes electrónicos con la norma internacional ISO 11784/11785. Antes de instalar conviene confirmar el tipo de arete que ya usan tus animales.",
  },
  {
    pregunta: "¿Qué equipo necesita mi rancho?",
    respuesta: "Fierro conecta un lector de aretes y una báscula con un equipo que registra los pesajes. La compatibilidad depende de los modelos y debe verificarse antes de instalarlos.",
  },
];

export default function PreguntasAcceso() {
  return (
    <div className="home-preguntas-acceso">
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
