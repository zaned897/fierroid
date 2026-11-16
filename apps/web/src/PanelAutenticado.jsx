import Admin from "./Admin.jsx";
import Animales from "./Animales.jsx";
import Asistente from "./Asistente.jsx";
import Dashboard from "./Dashboard.jsx";
import Estaciones from "./Estaciones.jsx";
import Pesajes from "./Pesajes.jsx";
import "./dashboard.css";

export default function PanelAutenticado({ session, vista, arete, onVista, onArete, onSalir, onExpired }) {
  const usuario = session.user || {};
  const cambiarVista = (nuevaVista) => {
    onArete(null);
    onVista(nuevaVista);
  };
  const abrirAnimal = (tag) => {
    onArete(tag);
    onVista("animales");
  };

  return (
    <Dashboard user={usuario} vista={vista} onVista={cambiarVista} onSalir={onSalir}>
      {vista === "pesajes" && <Pesajes key="pesajes" session={session} onExpired={onExpired} onHistorial={() => onVista("historial")} onEstaciones={() => onVista("estaciones")} />}
      {vista === "historial" && <Pesajes key="historial" session={session} onExpired={onExpired} historial onRecientes={() => onVista("pesajes")} />}
      {vista === "estaciones" && <Estaciones session={session} onExpired={onExpired} />}
      {vista === "animales" && <Animales key={arete || "hato"} session={session} onExpired={onExpired} arete={arete} />}
      {vista === "asistente" && <Asistente session={session} onExpired={onExpired} onAbrir={abrirAnimal} />}
      {vista === "admin" && usuario.is_superuser && <Admin session={session} onExpired={onExpired} />}
    </Dashboard>
  );
}
