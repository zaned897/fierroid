import usePanelResource from "./usePanelResource.js";
import { capturedLabel } from "./readings.js";
import { SIN_REPORTE_MIN, silentStations, stationStatus } from "./stations.js";
import "./funciones-panel.css";

const ETIQUETA = { reportando: "Reportando", "sin-reporte": "Sin reporte" };

export default function Estaciones({ session, onExpired }) {
  const { data, error, busy, refresh } = usePanelResource("/v1/devices", session, onExpired);
  return <section className="panel" aria-label="Estaciones">
    <div className="row dashboard-card-heading"><h2>Equipos registrados</h2><button type="button" onClick={refresh} disabled={busy}>{busy ? "Actualizando…" : "Actualizar"}</button></div>
    <p className="muted">Último reporte recibido de cada equipo. No confirma que siga conectado. "Sin reporte" significa más de {SIN_REPORTE_MIN} minutos sin noticias.</p>
    {error && <p className="error" role="alert">No se pudieron actualizar las estaciones. {error}</p>}
    {!data && !error && <p role="status">Cargando estaciones…</p>}
    {data?.devices?.length === 0 && <p className="dashboard-empty">Aún no hay reportes de estaciones.</p>}
    <ul className="dashboard-devices">{(data?.devices || []).map((device) => {
      const status = stationStatus(device);
      return <li key={device.device_id}>
        <div className="row estacion-cabeza"><h3>{device.device_id}</h3>{status && <span className={`estacion-estado ${status}`}>{ETIQUETA[status]}</span>}</div>
        <dl><div><dt>Último reporte</dt><dd>{capturedLabel(device.last_seen)}</dd></div><div><dt>Por enviar, en su último reporte</dt><dd>{device.pending_count ?? "Sin información"}</dd></div><div><dt>Versión del agente</dt><dd>{device.agent_version || "Sin información"}</dd></div></dl>
      </li>;
    })}</ul>
  </section>;
}

/** Aviso en el panel cuando una estación deja de reportar (#98). Sus pesajes siguen guardados en el equipo. */
export function AvisoEstaciones({ session, onExpired, onVer }) {
  const { data } = usePanelResource("/v1/devices", session, onExpired, 60000);
  const silent = silentStations(data?.devices);
  if (silent.length === 0) return null;
  return <div className="panel aviso-estaciones" role="status">
    <strong>{silent.length === 1 ? `${silent[0].device_id} no reporta` : `${silent.length} estaciones no reportan`} desde hace más de {SIN_REPORTE_MIN} minutos.</strong>
    <p>Los pesajes siguen guardados en el equipo y se envían cuando vuelve la conexión. Revisa la luz o la señal.</p>
    <button type="button" className="dashboard-text-button" onClick={onVer}>Ver estaciones →</button>
  </div>;
}
