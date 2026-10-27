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
    foto: "home-corral-ia",
  },
  {
    id: "venta",
    titulo: "Peso de venta",
    texto: "Tú pones la meta. Fierro cuenta cuántos ya llegaron y cuántos van cerca.",
    disponible: false,
    dato: "Meta 480 kg · 6 ya en peso",
    foto: "home-paisaje-ia",
  },
  {
    id: "equipo",
    titulo: "Tu equipo te avisa",
    texto: "El último reporte de cada estación y los pesajes que tiene por enviar.",
    disponible: true,
    dato: "Manga 1 · reportó hace 2 min",
    foto: "home-consulta-ia",
  },
  {
    id: "comprador",
    titulo: "Lista para el comprador",
    texto: "El lote pesado, arete por arete, listo para compartir.",
    disponible: false,
    dato: "Lote 3 · 40 animales · 17,480 kg",
    foto: "home-corral-v2-ia",
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
  const x0 = useRef(null);
  const [actual, setActual] = useState(0);
  const [previa, setPrevia] = useState(null);
  const [encima, setEncima] = useState(false);
  const [aLaVista, setALaVista] = useState(false);
  const [oculta, setOculta] = useState(false);

  const ir = (n) => {
    const siguiente = (n + IDEAS.length) % IDEAS.length;
    if (siguiente === actual) return;
    setPrevia(actual);
    setActual(siguiente);
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
    const observador = new IntersectionObserver(([e]) => setALaVista(e.isIntersecting), { threshold: 0.4 });
    observador.observe(nodo);
    return () => observador.disconnect();
  }, []);

  useEffect(() => {
    const cambio = () => setOculta(document.hidden);
    document.addEventListener("visibilitychange", cambio);
    return () => document.removeEventListener("visibilitychange", cambio);
  }, []);

  const pausa = encima || !aLaVista || oculta;

  return (
    <section className="bloque mas-que-bascula" id="mas-que-bascula" aria-labelledby="mqb-titulo" data-revelar>
      <div className="mqb-cabeza">
        <p className="mqb-ceja">Más que una báscula</p>
        <h2 id="mqb-titulo">Tus pesajes, convertidos en decisiones.</h2>
      </div>

      <div
        ref={raiz}
        className={`mqb-carrusel${pausa ? " pausa" : ""}`}
        role="region"
        aria-roledescription="carrusel"
        aria-label="Lo que Fierro hace con tus pesajes"
        tabIndex={0}
        onMouseEnter={() => setEncima(true)}
        onMouseLeave={() => setEncima(false)}
        onFocus={() => setEncima(true)}
        onBlur={(e) => { if (!e.currentTarget.contains(e.relatedTarget)) setEncima(false); }}
        onKeyDown={(e) => {
          if (e.key === "ArrowRight") ir(actual + 1);
          if (e.key === "ArrowLeft") ir(actual - 1);
        }}
        onPointerDown={(e) => { x0.current = e.clientX; }}
        onPointerUp={(e) => {
          const dx = x0.current === null ? 0 : e.clientX - x0.current;
          x0.current = null;
          if (Math.abs(dx) > DESLIZAR_PX) ir(actual + (dx < 0 ? 1 : -1));
        }}
      >
        <small className="mqb-marca">Ilustración generada con IA</small>

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
              aria-label={`${k + 1} de ${IDEAS.length}: ${idea.titulo}`}
              aria-hidden={k !== actual}
            >
              <img
                src={img.src}
                width={img.width}
                height={img.height}
                alt=""
                draggable="false"
                loading={k === 0 ? "eager" : "lazy"}
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
          <div className="mqb-pasos" role="tablist" aria-label="Ideas">
            {IDEAS.map((idea, k) => (
              <button
                key={idea.id}
                type="button"
                role="tab"
                aria-selected={k === actual}
                aria-controls={`mqb-${idea.id}`}
                className={`mqb-paso${k === actual ? " activo" : ""}${k < actual ? " visto" : ""}`}
                onClick={() => ir(k)}
              >
                <span
                  key={k === actual ? `activa-${actual}` : "quieta"}
                  className="mqb-barra"
                  onAnimationEnd={k === actual ? () => ir(actual + 1) : undefined}
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
