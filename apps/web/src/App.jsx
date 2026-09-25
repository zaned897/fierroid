import { useCallback, useEffect, useState } from "react";

import Admin from "./Admin.jsx";
import Animales from "./Animales.jsx";
import Home from "./Home.jsx";
import Login from "./Login.jsx";
import Dashboard from "./Dashboard.jsx";
import {
  clearSession,
  exchangeGoogleToken,
  loadSession,
  logout,
  saveSession,
} from "./auth.js";
import Pesajes from "./Pesajes.jsx";
import Estaciones from "./Estaciones.jsx";

/**
 * Rutas minimas, sin router.
 *
 * Son dos pantallas publicas. Una libreria de enrutamiento pesa mas en el
 * bundle -que se descarga en el corral, con senal mala- de lo que ahorra
 * frente a pushState y un listener de popstate.
 */
function useRuta() {
  const [ruta, setRuta] = useState(() => window.location.pathname);

  useEffect(() => {
    const alVolver = () => setRuta(window.location.pathname);
    window.addEventListener("popstate", alVolver);
    return () => window.removeEventListener("popstate", alVolver);
  }, []);

  const ir = useCallback((destino) => {
    window.history.pushState(null, "", destino);
    setRuta(destino);
  }, []);

  return [ruta, ir];
}

export default function App() {
  const [session, setSession] = useState(loadSession);
  const [vista, setVista] = useState("pesajes");
  const [ruta, ir] = useRuta();

  const entrar = useCallback(
    (nueva) => {
      saveSession(nueva);
      setSession(nueva);
      setVista("pesajes");
      // La URL deja de decir /entrar cuando ya entraste: recargar ahi no
      // debe devolver a una pantalla de login que ya no aplica.
      ir("/");
    },
    [ir],
  );

  const salir = useCallback(async () => {
    await logout(session);
    setSession(null);
    ir("/");
  }, [session, ir]);

  // Credencial revocada o expirada desde otro lado: se limpia sin llamar al
  // servidor, que ya nos dijo que no sirve.
  const expirada = useCallback(() => {
    clearSession();
    setSession(null);
  }, []);

  if (!session) {
    return ruta === "/entrar" ? (
      <Login onSession={entrar} exchange={exchangeGoogleToken} onInicio={() => ir("/")} />
    ) : (
      <Home onEntrar={() => ir("/entrar")} />
    );
  }

  const usuario = session.user || {};

  return (
    <Dashboard user={usuario} vista={vista} onVista={setVista} onSalir={salir}>
      {vista === "pesajes" && <Pesajes key="pesajes" session={session} onExpired={expirada} onHistorial={() => setVista("historial")} />}
      {vista === "historial" && <Pesajes key="historial" session={session} onExpired={expirada} historial onRecientes={() => setVista("pesajes")} />}
      {vista === "estaciones" && <Estaciones session={session} onExpired={expirada} />}
      {vista === "animales" && <Animales session={session} onExpired={expirada} />}
      {vista === "admin" && usuario.is_superuser && (
        <Admin session={session} onExpired={expirada} />
      )}
    </Dashboard>
  );
}
