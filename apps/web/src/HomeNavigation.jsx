import { useEffect, useRef, useState } from "react";

// Diccionario de la cabecera: permite traducir sus controles sin cambiar el JSX.
const messages = {
  es: {
    navigation: "Navegación principal",
    menu: "Menú",
    close: "Cerrar menú",
    login: "Iniciar sesión",
    join: "Unirme a la lista",
    links: [
      ["mas-que-bascula", "Lo que hace"],
      ["como-funciona", "Cómo funciona"],
      ["beneficios", "Beneficios"],
      ["por-que-pesar", "Por qué pesar"],
      ["fierro-vision", "Vision Premium"],
      ["preguntas-frecuentes", "Preguntas frecuentes"],
    ],
  },
};

function useCurrentSection(links) {
  const [current, setCurrent] = useState(null);

  useEffect(() => {
    const sections = links.map(([id]) => document.getElementById(id));
    if (!("IntersectionObserver" in window)) return undefined;
    // CSS ancla y desplaza el indicador; el observador aporta aria-current
    // también en móvil y sin anchor positioning. La sección más reciente que
    // cruzó la zona superior sigue activa también en los huecos entre secciones.
    let observer;
    const observe = () => {
      observer?.disconnect();
      const boundary = Math.round(window.innerHeight * 0.3);
      observer = new IntersectionObserver(() => {
        const passed = sections.filter((section) => section.getBoundingClientRect().top <= boundary);
        setCurrent(passed.at(-1)?.id ?? null);
      }, {
        // Los porcentajes de rootMargin se resuelven contra el ANCHO, no el alto.
        rootMargin: `0px 0px ${boundary - window.innerHeight}px 0px`,
        threshold: 0,
      });
      sections.forEach((section) => observer.observe(section));
    };
    observe();
    window.addEventListener("resize", observe);
    return () => {
      observer.disconnect();
      window.removeEventListener("resize", observe);
    };
  }, [links]);

  return current;
}

export default function HomeNavigation({ onEntrar, language = "es" }) {
  const copy = messages[language] ?? messages.es;
  const menu = useRef(null);
  const trigger = useRef(null);
  const login = useRef(null);
  const current = useCurrentSection(copy.links);
  const supportsPopover = Object.hasOwn(HTMLElement.prototype, "popover");
  const MenuSurface = supportsPopover ? "div" : "dialog";

  const closeMenu = () => {
    if (supportsPopover) menu.current.hidePopover();
    else menu.current.close();
    trigger.current.focus({ preventScroll: true });
  };

  useEffect(() => {
    const wide = window.matchMedia("(min-width: 1200px)");
    const closeOnResize = () => {
      const open = supportsPopover ? menu.current.matches(":popover-open") : menu.current.open;
      if (wide.matches && open) {
        if (supportsPopover) menu.current.hidePopover();
        else menu.current.close();
        login.current.focus({ preventScroll: true });
      }
    };
    wide.addEventListener("change", closeOnResize);
    return () => wide.removeEventListener("change", closeOnResize);
  }, [supportsPopover]);

  return (
    <>
      <nav className="home-navegacion" aria-label={copy.navigation}>
        {copy.links.map(([id, label]) => (
          <a key={id} href={`#${id}`} aria-current={current === id ? "location" : undefined}>{label}</a>
        ))}
      </nav>
      <div className="home-header-actions">
        <button ref={login} type="button" className="home-header-login" onClick={onEntrar}>{copy.login}</button>
        <a className="home-header-join" href="#lista-espera">{copy.join}</a>
        <button
          ref={trigger}
          type="button"
          className="home-menu-trigger"
          popoverTarget={supportsPopover ? "home-menu" : undefined}
          aria-haspopup={supportsPopover ? undefined : "dialog"}
          onClick={supportsPopover ? undefined : () => menu.current.showModal()}
        >{copy.menu}</button>
      </div>
      <MenuSurface ref={menu} id="home-menu" className="home-menu" popover={supportsPopover ? "auto" : undefined} aria-label={copy.navigation}>
        <button type="button" className="home-menu-close" onClick={closeMenu}>{copy.close}</button>
        <nav aria-label={copy.navigation}>
          {copy.links.map(([id, label]) => (
            <a key={id} href={`#${id}`} aria-current={current === id ? "location" : undefined} onClick={closeMenu}>{label}</a>
          ))}
        </nav>
        <a className="home-header-join" href="#lista-espera" onClick={closeMenu}>{copy.join}</a>
      </MenuSurface>
    </>
  );
}
