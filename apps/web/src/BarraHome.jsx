import { useEffect, useRef, useState } from "react";

import Marca from "./Marca.jsx";

const SECCIONES = [
  ["mas-que-bascula", "Lo que hace"],
  ["como-funciona", "Cómo funciona"],
  ["beneficios", "Beneficios"],
  ["por-que-pesar", "Por qué pesar"],
  ["fierro-vision", "Vision Premium"],
  ["preguntas-frecuentes", "Preguntas frecuentes"],
];
const MENU_COMPACTO = "(max-width: 70rem)";
const UMBRAL_PX = 8;

function useBarraConScroll() {
  const [estado, setEstado] = useState(() => ({
    arriba: window.scrollY < 24,
    oculta: false,
  }));

  useEffect(() => {
    let previo = window.scrollY;
    let cuadro = 0;
    const medir = () => {
      cuadro = 0;
      const y = window.scrollY;
      const arriba = y < 24;
      const delta = y - previo;
      if (Math.abs(delta) < UMBRAL_PX && !arriba) return;
      const enfocada = document.activeElement?.closest(".home-encabezado");
      const oculta = !arriba && delta > 0 && !enfocada;
      setEstado((actual) =>
        actual.arriba === arriba && actual.oculta === oculta ? actual : { arriba, oculta },
      );
      previo = y;
    };
    const alScroll = () => {
      if (!cuadro) cuadro = requestAnimationFrame(medir);
    };
    window.addEventListener("scroll", alScroll, { passive: true });
    return () => {
      window.removeEventListener("scroll", alScroll);
      cancelAnimationFrame(cuadro);
    };
  }, []);

  return estado;
}

function useSeccionActiva(encabezado) {
  const [activa, setActiva] = useState(null);

  useEffect(() => {
    if (!("IntersectionObserver" in window)) return undefined;
    const secciones = SECCIONES.map(([id]) => document.getElementById(id));
    let observador;
    const observar = () => {
      observador?.disconnect();
      // Una franja de 2 px bajo la barra evita depender del alto de cada sección.
      const inicio = Math.min(encabezado.current.offsetHeight + 24, window.innerHeight - 2);
      const fin = window.innerHeight - inicio - 2;
      observador = new IntersectionObserver(() => {
        const actual = secciones.find((seccion) => {
          const { top, bottom } = seccion.getBoundingClientRect();
          return top < inicio + 2 && bottom > inicio;
        });
        setActiva(actual?.id ?? null);
      }, { rootMargin: `-${inicio}px 0px -${fin}px 0px` });
      secciones.forEach((seccion) => observador.observe(seccion));
    };
    observar();
    window.addEventListener("resize", observar);
    return () => {
      window.removeEventListener("resize", observar);
      observador.disconnect();
    };
  }, [encabezado]);

  return activa;
}

export default function BarraHome({ onEntrar }) {
  const encabezado = useRef(null);
  const menu = useRef(null);
  const activa = useSeccionActiva(encabezado);
  const { arriba, oculta } = useBarraConScroll();
  const [compacta, setCompacta] = useState(() => window.matchMedia(MENU_COMPACTO).matches);
  const hayPopover = "popover" in HTMLElement.prototype;

  useEffect(() => {
    const media = window.matchMedia(MENU_COMPACTO);
    const cambiar = () => setCompacta(media.matches);
    media.addEventListener("change", cambiar);
    return () => media.removeEventListener("change", cambiar);
  }, []);

  const cerrarMenu = () => {
    if (!compacta) return;
    if (hayPopover) menu.current.hidePopover();
    else menu.current.open = false;
  };

  const links = SECCIONES.map(([id, etiqueta]) => (
    <li key={id}>
      <a href={`#${id}`} aria-current={activa === id ? "location" : undefined} onClick={cerrarMenu}>
        {etiqueta}
      </a>
    </li>
  ));
  const entrar = (
    <button type="button" className="home-login" onClick={onEntrar}>Iniciar sesión</button>
  );
  const clase = `home-encabezado${arriba ? "" : " fija"}${oculta ? " oculta" : ""}`;

  return (
    <header className={clase} ref={encabezado}>
      <a className="home-marca" href="/" aria-label="Fierro, inicio">
        <Marca size={38} />
        <span>Fierro</span>
      </a>
      <nav className="home-navegacion" aria-label="Navegación principal">
        {!compacta ? (
          <ul className="home-enlaces">{links}</ul>
        ) : hayPopover ? (
          <>
            <button type="button" className="home-menu-abrir" popoverTarget="home-menu" aria-controls="home-menu">
              <span aria-hidden="true" className="home-menu-icono" />
              Menú
            </button>
            <ul className="home-enlaces home-menu" id="home-menu" popover="auto" ref={menu}>
              {links}
              <li>{entrar}</li>
            </ul>
          </>
        ) : (
          <details ref={menu} className="home-menu-respaldo">
            <summary className="home-menu-abrir">Menú</summary>
            <ul className="home-enlaces home-menu">
              {links}
              <li>{entrar}</li>
            </ul>
          </details>
        )}
      </nav>
      {!compacta && entrar}
      <a className="home-cta" href="#lista-espera">Unirme a la lista</a>
    </header>
  );
}
