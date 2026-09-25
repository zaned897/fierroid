import usePanelResource from "./usePanelResource.js";
import { capturedLabel } from "./readings.js";

export default function Estaciones({ session, onExpired }) {
  const { data, error, busy, refresh } = usePanelResource("/v1/devices", session, onExpired);
  return <section className="panel" aria-label="Estaciones">
    <div className="row dashboard-card-heading"><h2>Equipos registrados</h2><button type="button" onClick={refresh} disabled={busy}>{busy ? "Actualizando…" : "Actualizar"}</button></div>
    <p className="muted">Último reporte recibido de cada equipo. No confirma que siga conectado.</p>
    {error && <p className="error" role="alert">No se pudieron actualizar las estaciones. {error}</p>}
    {!data && !error && <p role="status">Cargando estaciones…</p>}
    {data?.devices?.length === 0 && <p className="dashboard-empty">Aún no hay reportes de estaciones.</p>}
    <ul className="dashboard-devices">{(data?.devices || []).map((device) => <li key={device.device_id}>
      <h3>{device.device_id}</h3>
      <dl><div><dt>Último reporte</dt><dd>{capturedLabel(device.last_seen)}</dd></div><div><dt>Pendientes de envío</dt><dd>{device.pending_count ?? "Sin información"}</dd></div><div><dt>Versión del agente</dt><dd>{device.agent_version || "Sin información"}</dd></div></dl>
    </li>)}</ul>
  </section>;
}
