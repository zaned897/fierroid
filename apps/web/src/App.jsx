import { useCallback, useEffect, useState } from "react";

import { CowForTag, CowIcon } from "./icons/cows.jsx";

const API_BASE = import.meta.env.VITE_API_BASE || "";

async function fetchJson(path) {
  const res = await fetch(`${API_BASE}${path}`);
  if (!res.ok) throw new Error(`${res.status} ${path}`);
  return res.json();
}

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

export default function App() {
  const [readings, setReadings] = useState([]);
  const [devices, setDevices] = useState([]);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(true);

  const refresh = useCallback(async () => {
    try {
      const [r, d] = await Promise.all([
        fetchJson("/v1/readings?limit=40"),
        fetchJson("/v1/devices"),
      ]);
      setReadings(r.readings || []);
      setDevices(d.devices || []);
      setError(null);
    } catch (err) {
      setError(err.message || "Error de red");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    refresh();
    const id = setInterval(refresh, 3000);
    return () => clearInterval(id);
  }, [refresh]);

  return (
    <div className="page">
      <header className="hero">
        <div className="brand-row">
          <CowIcon variant="frente" size={40} className="cow" />
          <p className="brand">Fierro</p>
        </div>
        <h1>Pesajes</h1>
        <p className="lede">Lecturas RFID + peso sincronizadas desde el corral.</p>
      </header>

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
    </div>
  );
}
