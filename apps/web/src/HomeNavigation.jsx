import { useEffect, useId, useRef, useState } from "react";
import { homeNavigationText as text } from "./homeNavigationText.js";
import "./home-navigation.css";

// Los seis destinos y las dos acciones necesitan más espacio que la barra anterior.
const COMPACT_QUERY = "(max-width: 1199px)";

export default function HomeNavigation() {
  const id = useId();
  const panel = useRef(null);
  const trigger = useRef(null);
  const links = useRef(null);
  const [compact, setCompact] = useState(() => matchMedia(COMPACT_QUERY).matches);
  const supportsPopover = "popover" in HTMLElement.prototype;
  const Panel = supportsPopover ? "div" : "dialog";

  useEffect(() => {
    const media = matchMedia(COMPACT_QUERY);
    const resize = () => {
      // Cerrar antes de cambiar de presentación, incluso si el foco estaba dentro.
      const focused = panel.current.contains(document.activeElement);
      if (supportsPopover) {
        if (panel.current.matches(":popover-open")) panel.current.hidePopover();
      } else if (panel.current.open) {
        panel.current.close();
      }
      setCompact(media.matches);
      if (focused) {
        requestAnimationFrame(() => {
          (media.matches ? trigger.current : links.current?.querySelector("a"))?.focus();
        });
      }
    };
    media.addEventListener("change", resize);
    return () => media.removeEventListener("change", resize);
  }, [supportsPopover]);

  useEffect(() => {
    const container = links.current;
    const menu = panel.current;
    const anchors = [...container.querySelectorAll("a")];
    const sections = anchors.map((link) => document.querySelector(link.hash));
    const native = CSS.supports("scroll-target-group: auto") && CSS.supports("selector(:target-current)");
    const sync = () => {
      // CSS elige el destino; JS solo comunica ese mismo estado al lector de pantalla.
      const current = native
        ? container.querySelector(":target-current")
        : anchors[sections.findLastIndex((section) => section.getBoundingClientRect().top <= window.innerHeight * 0.2 + 1)];
      anchors.forEach((link) => {
        if (link === current) link.setAttribute("aria-current", "location");
        else link.removeAttribute("aria-current");
      });
    };
    const frame = requestAnimationFrame(sync);
    let observer;
    const observe = () => {
      observer?.disconnect();
      // Los porcentajes de rootMargin se calculan sobre el ANCHO del viewport.
      // Usar píxeles mantiene la línea de lectura al 20% de su altura.
      const line = Math.round(window.innerHeight * 0.2);
      observer = new IntersectionObserver(sync, {
        rootMargin: `-${line}px 0px -${window.innerHeight - line - 1}px 0px`,
      });
      sections.forEach((section) => observer.observe(section));
      sync();
    };
    if (native) {
      document.addEventListener("scrollend", sync);
    } else {
      // Respaldo sin listeners de scroll; también reacciona a cambios de tamaño.
      observe();
    }
    const resize = native ? sync : observe;
    window.addEventListener("resize", resize);
    menu.addEventListener("toggle", sync);
    return () => {
      cancelAnimationFrame(frame);
      document.removeEventListener("scrollend", sync);
      window.removeEventListener("resize", resize);
      menu.removeEventListener("toggle", sync);
      observer?.disconnect();
    };
  }, [compact]);

  const close = () => {
    if (!compact) return;
    if (supportsPopover) panel.current.hidePopover();
    else panel.current.close();
  };
  const navigate = (event) => {
    const link = event.target.closest("a");
    if (!link) return;
    close();
    // Al elegir un destino, continuar el recorrido de teclado desde el contenido.
    const target = document.querySelector(link.hash);
    target.tabIndex = -1;
    target.focus({ preventScroll: true });
  };

  return (
    <nav className="home-navegacion" aria-label={text.label}>
      <button
        ref={trigger}
        className="home-menu-trigger"
        type="button"
        aria-controls={id}
        popoverTarget={supportsPopover && compact ? id : undefined}
        onClick={supportsPopover ? undefined : () => panel.current.showModal()}
      >
        <span aria-hidden="true">☰</span> {text.menu}
      </button>
      <Panel
        ref={panel}
        id={id}
        className="home-menu-panel"
        popover={supportsPopover && compact ? "auto" : undefined}
        open={!supportsPopover && !compact ? true : undefined}
        role={!compact ? "presentation" : undefined}
        aria-label={!supportsPopover && compact ? text.label : undefined}
        onClick={navigate}
      >
        <button className="home-menu-close" type="button" onClick={close}>{text.close}</button>
        <div className="home-nav-links" ref={links}>
          {text.links.map(([target, label]) => <a key={target} href={`#${target}`}>{label}</a>)}
        </div>
        <a className="home-entrar home-menu-waitlist" href="#lista-espera">{text.waitlist}</a>
      </Panel>
    </nav>
  );
}
