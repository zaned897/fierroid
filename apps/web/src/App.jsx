import { useCallback, useEffect, useState } from "react";

import Login from "./Login.jsx";
import {
  apiFetch,
  clearSession,
  exchangeGoogleToken,
  loadSession,
  logout,
  saveSession,
} from "./auth.js";
import { CowForTag, CowIcon } from "./icons/cows.jsx";

function formatKg(kg) {
  return `${Number(kg).toFixed(1)} kg`;
}

function formatWhen(iso) {
  try {
    return new Date(iso).toLocaleString();
  } catch {
    return iso;
  }
}

function Pesajes({ session, onExpired }) {
  const [readings, setReadings] = useState([]);
  const [devices, setDevices] = useState([]);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(true);

  const refresh = useCallback(async () => {
    try {
      const [r, d] = await Promise.all([
        apiFetch("/v1/readings?limit=40", { session }),
        apiFetch("/v1/devices", { session }),
      ]);
      setReadings(r.readings || []);
      setDevices(d.devices || []);
      setError(null);
    } catch (err) {
      if (err.unauthorized) {
        // La credencial dejó de servir: no tiene caso seguir consultando.
        onExpired();
        return;
      }
      setError(err.message || "Error de red");
    } finally {
      setLoading(false);
    }
  }, [session, onExpired]);

  useEffect(() => {
    refresh();
    const id = setInterval(refresh, 3000);
    return () => clearInterval(id);
  }, [refresh]);

  return (
    <>
      <section className="panel" aria-label="Dispositivos">
        <h2>Dispositivos</h2>
        {devices.length === 0 ? (
          <p className="muted">Sin heartbeats aún.</p>
        ) : (
          <ul className="device-list">
            {devices.map((d) => (
              <li key={d.device_id}>
                <strong>{d.device_id}</strong>
                <span>cola {d.pending_count}</span>
                <span>v{d.agent_version || "?"}</span>
              </li>
            ))}
          </ul>
        )}
      </section>

      <section className="panel" aria-label="Lecturas">
        <div className="row">
          <h2>Últimas lecturas</h2>
          <button type="button" onClick={refresh}>
            Actualizar
          </button>
        </div>
        {loading && <p className="muted">Cargando…</p>}
        {error && <p className="error">{error}</p>}
        {!loading && readings.length === 0 && (
          <p className="empty">
            <CowIcon variant="becerro" size={52} className="cow" />
            Todavía no hay pesajes. Arranca el agent mock.
          </p>
        )}
        <ul className="reading-list">
          {readings.map((r) => (
            <li key={r.event_id}>
              {/* Mismo arete, mismo dibujo: ancla visual para reconocer al animal. */}
              <CowForTag tagId={r.tag_id} size={34} className="cow" />
              <div className="reading-body">
                <div className="weight">
                  {formatKg(r.weight_kg)}
                  {/* La API ya manda `stable`; ocultarlo seria esconder un dato malo. */}
                  {!r.stable && <span className="badge">inestable</span>}
                </div>
                <div className="meta">
                  <span className="tag">{r.tag_id}</span>
                  <span>{r.device_id}</span>
                  <span>{formatWhen(r.captured_at)}</span>
                </div>
              </div>
            </li>
          ))}
        </ul>
      </section>
    </>
  );
}

export default function App() {
  const [session, setSession] = useState(loadSession);

  const entrar = useCallback((nueva) => {
    saveSession(nueva);
    setSession(nueva);
  }, []);

  const salir = useCallback(async () => {
    await logout(session);
    setSession(null);
  }, [session]);

  // Credencial revocada o expirada desde otro lado: se limpia sin llamar al
  // servidor, que ya nos dijo que no sirve.
  const expirada = useCallback(() => {
    clearSession();
    setSession(null);
  }, []);

  if (!session) {
    return <Login onSession={entrar} exchange={exchangeGoogleToken} />;
  }

  const usuario = session.user || {};

  return (
    <div className="page">
      <header className="hero">
        <div className="brand-row">
          <CowIcon variant="frente" size={40} className="cow" />
          <p className="brand">Fierro</p>
          <button type="button" className="ghost" onClick={salir}>
            Salir
          </button>
        </div>
        <h1>Pesajes</h1>
        <p className="lede">
          {usuario.is_superuser ? "Todas las organizaciones" : usuario.org || "Sin organización"}
          {" · "}
          {usuario.email}
        </p>
      </header>

      <Pesajes session={session} onExpired={expirada} />
    </div>
  );
}
