import { useEffect, useRef } from "react";
import Marca from "./Marca.jsx";
import { CowIcon } from "./icons/cows.jsx";

const sections = [
  ["pesajes", "Pesajes"],
  ["animales", "Animales"],
  ["estaciones", "Estaciones"],
  ["historial", "Historial"],
  ["admin", "Administración"],
];

export function PanelIcon({ name }) {
  if (name === "animales") return <CowIcon size={24} />;
  const paths = {
    pesajes: "M12 3v18M5 21h14M3 7h18M6 7l-4 9h8L6 7Zm12 0-4 9h8l-4-9Z",
    estaciones: "M5 3v18M19 3v18M2 7h20M2 12h20M2 17h20",
    historial: "M6 3h8l4 4v14H6V3Zm8 0v5h4M9 12h6M9 16h6",
    admin: "M4 7h16M4 17h16M8 4v6M16 14v6",
    cuenta: "M4 21v-3a8 8 0 0 1 16 0v3M16 7a4 4 0 1 1-8 0 4 4 0 0 1 8 0Z",
    salir: "M10 4H4v16h6M8 12h13M16 7l5 5-5 5",
  };
  return <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><path d={paths[name] || paths.cuenta} /></svg>;
}

export default function Dashboard({ user, vista, onVista, onSalir, children }) {
  const heading = useRef(null);
  const previousView = useRef(vista);
  useEffect(() => {
    if (previousView.current !== vista) {
      heading.current?.focus({ preventScroll: true });
      window.scrollTo({ top: 0 });
      previousView.current = vista;
    }
  }, [vista]);
  const available = sections.filter(([id]) => id !== "admin" || user.is_superuser);
  const title = sections.find(([id]) => id === vista)?.[1] || "Pesajes";
  const context = user.is_superuser ? "Todas las organizaciones" : user.org || "Sin organización";
  return (
    <div className="dashboard">
      <a className="dashboard-skip" href="#panel-contenido">Saltar al contenido</a>
      <aside className="dashboard-sidebar">
        <div className="dashboard-brand"><Marca size={36} /><span>FIERRO</span></div>
        <nav className="dashboard-nav" aria-label="Secciones del panel">
          {available.map(([id, label]) => <button className={id === "admin" || id === "historial" ? "dashboard-desktop-destination" : ""} key={id} type="button" aria-current={vista === id ? "page" : undefined} onClick={() => onVista(id)}><PanelIcon name={id} /><span>{label}</span></button>)}
          <details className="dashboard-more" key={vista}>
            <summary className={vista === "historial" || vista === "admin" ? "is-active" : ""}><span aria-hidden="true">•••</span>Más</summary>
            <div><button type="button" onClick={() => onVista("historial")} aria-current={vista === "historial" ? "page" : undefined}><PanelIcon name="historial" />Historial</button>{user.is_superuser && <button type="button" onClick={() => onVista("admin")} aria-current={vista === "admin" ? "page" : undefined}><PanelIcon name="admin" />Administración</button>}</div>
          </details>
        </nav>
        <button type="button" className="dashboard-exit" onClick={onSalir}><PanelIcon name="salir" />Cerrar sesión</button>
      </aside>
      <div className="dashboard-workspace">
        <header className="dashboard-topbar">
          <div className="dashboard-mobile-brand"><Marca size={30} /><strong>FIERRO</strong></div>
          <div className="dashboard-context"><span>Organización</span><strong>{context}</strong></div>
          <details className="dashboard-account">
            <summary><PanelIcon name="cuenta" /><span>Cuenta</span><span aria-hidden="true">⌄</span></summary>
            <div className="dashboard-account-menu">
              <strong>{user.full_name || "Tu cuenta"}</strong>
              <span>{user.email}</span>
              <span className="muted">{user.is_superuser ? "Superusuario" : "Usuario"} · {context}</span>
              <button type="button" onClick={onSalir}>Cerrar sesión</button>
            </div>
          </details>
        </header>
        <main id="panel-contenido" className="dashboard-main" tabIndex={-1}>
          <h1 ref={heading} tabIndex={-1}>{title}</h1>
          {children}
        </main>
      </div>
    </div>
  );
}
