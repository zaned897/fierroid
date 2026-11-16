import { lazy, Suspense, useCallback, useEffect, useState } from "react";

import Home from "./Home.jsx";
import Login from "./Login.jsx";
import {
  clearSession,
  exchangeGoogleToken,
  loadSession,
  logout,
  saveSession,
} from "./auth.js";
import Entorno from "./Entorno.jsx";

const PanelAutenticado = lazy(() => import("./PanelAutenticado.jsx"));

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
  return <><Entorno /><Contenido /></>;
}

function Contenido() {
  const [session, setSession] = useState(loadSession);
  const [vista, setVista] = useState("pesajes");
  // Arete que el asistente pidió abrir; se olvida al cambiar de vista desde el menú.
  const [arete, setArete] = useState(null);
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

  return (
    <Suspense fallback={<main className="panel" role="status">Cargando panel…</main>}>
      <PanelAutenticado
        session={session}
        vista={vista}
        arete={arete}
        onVista={setVista}
        onArete={setArete}
        onSalir={salir}
        onExpired={expirada}
      />
    </Suspense>
  );
}
