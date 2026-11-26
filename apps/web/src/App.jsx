import { useCallback, useEffect, useState } from "react";

import Admin from "./Admin.jsx";
import Animales from "./Animales.jsx";
import Asistente from "./Asistente.jsx";
import Home from "./Home.jsx";
import Login from "./Login.jsx";
import Dashboard from "./Dashboard.jsx";
import {
  apiFetch,
  clearSession,
  exchangeGoogleToken,
  loadSession,
  logout,
  saveSession,
} from "./auth.js";
import Pesajes from "./Pesajes.jsx";
import Estaciones from "./Estaciones.jsx";
import Entorno from "./Entorno.jsx";
import { demoActivo, demoInicial } from "./demo.js";

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

  // Al abrir: refresca la cuenta (una sesión guardada antes de 016 no sabe de
  // su rancho demo) y, la primera vez, decide si arranca en demo.
  const sesionId = session?.id;
  useEffect(() => {
    if (!sesionId) return undefined;
    const controller = new AbortController();
    (async () => {
      const actual = loadSession();
      if (!actual) return;
      const user = await apiFetch("/v1/auth/me", { session: actual, signal: controller.signal });
      let demo = actual.demo;
      if (!user.demo_org) {
        demo = false;
      } else if (demo === undefined) {
        const reales = await apiFetch("/v1/readings?limit=1", {
          session: actual, real: true, signal: controller.signal,
        });
        demo = demoInicial(user, reales.readings.length);
      }
      const nueva = { ...actual, user, demo };
      saveSession(nueva);
      setSession(nueva);
    })().catch((error) => {
      if (error.unauthorized) expirada();
      // Otro fallo (red, abort): se queda la sesión guardada, que ya sirve.
    });
    return () => controller.abort();
  }, [sesionId, expirada]);

  const cambiarDemo = useCallback(() => {
    setSession((actual) => {
      const nueva = { ...actual, demo: !actual.demo };
      saveSession(nueva);
      return nueva;
    });
  }, []);

  if (!session) {
    return ruta === "/entrar" ? (
      <Login onSession={entrar} exchange={exchangeGoogleToken} onInicio={() => ir("/")} />
    ) : (
      <Home onEntrar={() => ir("/entrar")} />
    );
  }

  const usuario = session.user || {};
  const demo = usuario.demo_org
    ? { activo: demoActivo(session), org: usuario.demo_org, onCambiar: cambiarDemo }
    : null;

  return (
    <Dashboard user={usuario} demo={demo} vista={vista} onVista={(v) => { setArete(null); setVista(v); }} onSalir={salir}>
      {/* La clave remonta la vista al cambiar de rancho: nada de lo cargado
          del rancho anterior sobrevive al cambio. */}
      <div key={demoActivo(session) ? "demo" : "real"} className="dashboard-vista">
      {vista === "pesajes" && <Pesajes key="pesajes" session={session} onExpired={expirada} onHistorial={() => setVista("historial")} onEstaciones={() => setVista("estaciones")} />}
      {vista === "historial" && <Pesajes key="historial" session={session} onExpired={expirada} historial onRecientes={() => setVista("pesajes")} />}
      {vista === "estaciones" && <Estaciones session={session} onExpired={expirada} />}
      {vista === "animales" && <Animales key={arete || "hato"} session={session} onExpired={expirada} arete={arete} />}
      {vista === "asistente" && <Asistente session={session} onExpired={expirada} onAbrir={(tag) => { setArete(tag); setVista("animales"); }} />}
      {vista === "admin" && usuario.is_superuser && (
        <Admin session={session} onExpired={expirada} />
      )}
      </div>
    </Dashboard>
  );
}
