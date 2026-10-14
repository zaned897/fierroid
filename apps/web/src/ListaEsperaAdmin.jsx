import { useRef, useState } from "react";
import { apiFetch, apiUrl } from "./auth.js";

export default function ListaEsperaAdmin({ session, onExpired }) {
  const [entries, setEntries] = useState([]);
  const [cursor, setCursor] = useState(null);
  const [loaded, setLoaded] = useState(false);
  const [busy, setBusy] = useState(false);
  const [downloading, setDownloading] = useState(false);
  const [error, setError] = useState('');
  const request = useRef(false);
  async function load(next = null) {
    if (request.current) return;
    request.current = true; setBusy(true); setError('');
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), 15000);
    try {
      const data = await apiFetch(`/v1/admin/waitlist${next ? `?before=${next}` : ''}`, { session, signal: controller.signal });
      setEntries((old) => next ? [...old, ...data.entries] : data.entries);
      setCursor(data.next_cursor); setLoaded(true);
    } catch (err) {
      if (err.unauthorized) onExpired();
      else setError('No se pudo cargar la lista de espera.');
    } finally { clearTimeout(timer); request.current = false; setBusy(false); }
  }
  async function downloadExcel() {
    setDownloading(true); setError('');
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), 20000);
    try {
      const headers = {};
      if (session?.api_key) headers.Authorization = `Bearer ${session.api_key}`;
      const response = await fetch(apiUrl('/v1/admin/waitlist.xlsx'), { headers, signal: controller.signal });
      if (response.status === 401) {
        onExpired();
        return;
      }
      if (!response.ok) throw new Error(`${response.status}`);
      const blob = await response.blob();
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `lista-espera-fierro-${new Date().toISOString().slice(0, 10)}.xlsx`;
      document.body.appendChild(link);
      link.click();
      link.remove();
      URL.revokeObjectURL(url);
    } catch {
      setError('No se pudo descargar la hoja de Excel.');
    } finally { clearTimeout(timer); setDownloading(false); }
  }
  return <section className="panel" aria-label="Lista de espera">
    <h2>Lista de espera</h2><p>Interesados sin cuenta de acceso. Registrar interés no reserva equipo.</p>
    <div className="waitlist-admin-actions">
      <button type="button" disabled={busy} onClick={() => load()}>{busy ? 'Cargando…' : 'Consultar lista'}</button>
      <button type="button" disabled={downloading} onClick={downloadExcel}>{downloading ? 'Preparando…' : 'Descargar Excel'}</button>
    </div>
    {error && <p role="alert" className="error">{error}</p>}
    {loaded && entries.length === 0 && <p>Aún no hay registros.</p>}
    <ul className="waitlist-admin-list">{entries.map((entry) => <li key={entry.id}><div><strong>{entry.name}</strong><p>{entry.email} · {entry.state} · {entry.stations} estaciones</p><small>{new Date(entry.created_at).toLocaleString('es-MX')}</small></div><span className={`waitlist-status ${entry.confirmed_at ? 'is-confirmed' : 'is-pending'}`}>{entry.confirmed_at ? 'Confirmado' : 'Pendiente'}</span></li>)}</ul>
    {cursor && <button type="button" disabled={busy} onClick={() => load(cursor)}>Ver anteriores</button>}
  </section>;
}
