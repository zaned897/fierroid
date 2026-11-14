import { useEffect, useRef, useState } from "react";

import { imagenes } from "./img/index.js";
import "./mas-que-bascula.css";

/**
 * Lo que sale de los pesajes además del registro (#93, #94), como carrusel
 * (propuesta K del diseño del home). Una idea por pantalla: título, una frase,
 * su estado real y un dato de ejemplo. Cada idea dice si está disponible, con
 * la misma regla que Fierro Vision: lo que aún no se construye no se presenta
 * como disponible. Los datos son ejemplos fijos, sin consultas a ningún rancho.
 */
const IDEAS = [
  {
    id: "atras",
    titulo: "Animales que se quedan atrás",
    texto: "Al terminar la jornada, quiénes no ganaron peso desde el último pesaje.",
    disponible: false,
    dato: "3 animales para revisar",
    foto: "mqb-atras-ia",
  },
  {
    id: "venta",
    titulo: "Peso de venta",
    texto: "Tú pones la meta. Fierro cuenta cuántos ya llegaron y cuántos van cerca.",
    disponible: false,
    dato: "Meta 480 kg · 6 ya en peso",
    foto: "mqb-venta-ia",
  },
  {
    id: "equipo",
    titulo: "Tu equipo te avisa",
    texto: "El último reporte de cada estación y los pesajes que tiene por enviar.",
    disponible: true,
    dato: "Manga 1 · reportó hace 2 min",
    foto: "mqb-equipo-ia",
  },
  {
    id: "comprador",
    titulo: "Lista para el comprador",
    texto: "El lote pesado, arete por arete, listo para compartir.",
    disponible: false,
    dato: "Lote 3 · 40 animales · 17,480 kg",
    foto: "mqb-comprador-ia",
  },
];

/** Lo que tarda la cortina; coincide con la transición de .mqb-slide. */
const CORTINA_MS = 1100;
/** Distancia mínima del dedo para contar como deslizar y no como toque. */
const DESLIZAR_PX = 40;

/**
 * El avance automático no usa temporizadores: lo marca la animación de la
 * barra de la pestaña activa, y al terminar pasa a la siguiente. Pausar es
 * pausar esa animación, así la barra y el cambio nunca se desfasan. Con
 * movimiento reducido la barra no anima y el carrusel no avanza solo.
 */
export default function MasQueBascula() {
  const raiz = useRef(null);
  const gesto = useRef(null);
  const [actual, setActual] = useState(0);
  const [previa, setPrevia] = useState(null);
  const [reproduccion, setReproduccion] = useState("automatica");
  const [aLaVista, setALaVista] = useState(false);
  const [oculta, setOculta] = useState(() => document.hidden);

  const ir = (n) => {
    const siguiente = (n + IDEAS.length) % IDEAS.length;
    if (siguiente !== actual) {
      setPrevia(actual);
      setActual(siguiente);
    }
    return siguiente;
  };

  useEffect(() => {
    if (previa === null) return undefined;
    const t = setTimeout(() => setPrevia(null), CORTINA_MS + 50);
    return () => clearTimeout(t);
  }, [previa]);

  useEffect(() => {
    const nodo = raiz.current;
    if (!nodo || !("IntersectionObserver" in window)) {
      setALaVista(true);
      return undefined;
    }
    const observador = new IntersectionObserver(
      ([e]) => setALaVista(e.intersectionRatio >= 0.4),
      { threshold: 0.4 },
    );
    observador.observe(nodo);
    return () => observador.disconnect();
  }, []);

  useEffect(() => {
    const cambio = () => setOculta(document.hidden);
    document.addEventListener("visibilitychange", cambio);
    return () => document.removeEventListener("visibilitychange", cambio);
  }, []);

  const detenida = reproduccion === "pausada";
  const pausa = detenida || !aLaVista || oculta;

  return (
    <section className="bloque mas-que-bascula" id="mas-que-bascula" aria-labelledby="mqb-titulo" data-revelar>
      <div
        ref={raiz}
        className={`mqb-carrusel${pausa ? " pausa" : ""}${reproduccion === "reanudada" ? " reanudado" : ""}`}
        role="region"
        aria-roledescription="carrusel"
        aria-label="Lo que Fierro hace con tus pesajes"
        tabIndex={0}
        onKeyDown={(e) => {
          const pestanas = e.target.closest('[role="tablist"]');
          let siguiente;
          if (e.key === "ArrowRight") siguiente = actual + 1;
          else if (e.key === "ArrowLeft") siguiente = actual - 1;
          else if (pestanas && e.key === "Home") siguiente = 0;
          else if (pestanas && e.key === "End") siguiente = IDEAS.length - 1;
          else return;
          e.preventDefault();
          const indice = ir(siguiente);
          pestanas?.querySelectorAll('[role="tab"]')[indice].focus();
        }}
        onPointerDown={(e) => {
          if (e.pointerType !== "touch" || !e.isPrimary || e.target.closest("button")) return;
          gesto.current = { id: e.pointerId, x: e.clientX, y: e.clientY };
        }}
        onPointerUp={(e) => {
          if (gesto.current?.id !== e.pointerId) return;
          const dx = e.clientX - gesto.current.x;
          const dy = e.clientY - gesto.current.y;
          gesto.current = null;
          if (Math.abs(dx) > Math.max(DESLIZAR_PX, Math.abs(dy))) ir(actual + (dx < 0 ? 1 : -1));
        }}
        onPointerCancel={(e) => { if (gesto.current?.id === e.pointerId) gesto.current = null; }}
      >
        <div className="mqb-cabeza">
          <p className="mqb-ceja">Más que una báscula</p>
          <h2 id="mqb-titulo">Tus pesajes, convertidos en decisiones.</h2>
        </div>
        {IDEAS.map((idea, k) => {
          const img = imagenes[idea.foto];
          const estado = k === actual ? " activa" : k === previa ? " sale" : "";
          return (
            <div
              key={idea.id}
              id={`mqb-${idea.id}`}
              className={`mqb-slide${estado}`}
              role="tabpanel"
              aria-roledescription="idea"
              aria-labelledby={`mqb-pestana-${idea.id}`}
              aria-hidden={k !== actual}
            >
              <img
                src={img.src}
                width={img.width}
                height={img.height}
                alt=""
                draggable="false"
                loading="lazy"
                decoding="async"
              />
              <div className="mqb-texto">
                <span className="mqb-linea"><span className="mqb-num">{`0${k + 1} / 0${IDEAS.length}`}</span></span>
                <span className="mqb-linea"><h3>{idea.titulo}</h3></span>
                <span className="mqb-linea"><p>{idea.texto}</p></span>
                <span className="mqb-linea">
                  <span className="mqb-pie">
                    <span className={`mqb-estado${idea.disponible ? " mqb-disponible" : ""}`}>
                      {idea.disponible ? "Disponible" : "Próximamente"}
                    </span>
                    <span className="mqb-dato">{idea.dato}<small>ejemplo</small></span>
                  </span>
                </span>
              </div>
            </div>
          );
        })}

        <div className="mqb-nav">
          <button
            type="button"
            className="mqb-flecha mqb-reproducir"
            aria-label={detenida ? "Reproducir carrusel" : "Pausar carrusel"}
            onClick={() => setReproduccion(detenida ? "reanudada" : "pausada")}
            onBlur={() => { if (reproduccion === "reanudada") setReproduccion("automatica"); }}
          >
            <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
              <path d={detenida ? "M8 5v14l11-7z" : "M7 5h3v14H7zm7 0h3v14h-3z"} />
            </svg>
          </button>
          <div className="mqb-pasos" role="tablist" aria-label="Ideas">
            {IDEAS.map((idea, k) => (
              <button
                key={idea.id}
                type="button"
                role="tab"
                id={`mqb-pestana-${idea.id}`}
                aria-label={`${k + 1} de ${IDEAS.length}: ${idea.titulo}`}
                aria-selected={k === actual}
                aria-controls={`mqb-${idea.id}`}
                tabIndex={k === actual ? 0 : -1}
                className={`mqb-paso${k === actual ? " activo" : ""}${k < actual ? " visto" : ""}`}
                onClick={() => ir(k)}
              >
                <span
                  key={k === actual ? `activa-${actual}` : "quieta"}
                  className="mqb-barra"
                  onAnimationEnd={k === actual && !pausa ? () => ir(actual + 1) : undefined}
                />
                <span className="mqb-paso-nombre">{idea.titulo}</span>
              </button>
            ))}
          </div>
          <div className="mqb-flechas">
            <button type="button" className="mqb-flecha" aria-label="Idea anterior" onClick={() => ir(actual - 1)}>
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true"><path d="M15 18l-6-6 6-6" /></svg>
            </button>
            <button type="button" className="mqb-flecha" aria-label="Idea siguiente" onClick={() => ir(actual + 1)}>
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true"><path d="M9 18l6-6-6-6" /></svg>
            </button>
          </div>
        </div>
      </div>
    </section>
  );
}
