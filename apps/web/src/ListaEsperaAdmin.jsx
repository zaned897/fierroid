import { useRef, useState } from "react";
import { apiFetch } from "./auth.js";

export default function ListaEsperaAdmin({ session, onExpired }) {
  const [entries, setEntries] = useState([]);
  const [cursor, setCursor] = useState(null);
  const [loaded, setLoaded] = useState(false);
  const [busy, setBusy] = useState(false);
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
  return <section className="panel" aria-label="Lista de espera">
    <h2>Lista de espera</h2><p>Interesados sin cuenta de acceso. Registrar interés no reserva equipo.</p>
    <button type="button" disabled={busy} onClick={() => load()}>{busy ? 'Cargando…' : 'Consultar lista'}</button>
    {error && <p role="alert" className="error">{error}</p>}
    {loaded && entries.length === 0 && <p>Aún no hay registros.</p>}
    <ul>{entries.map((entry) => <li key={entry.id}><strong>{entry.name}</strong><p>{entry.email} · {entry.stations} estaciones</p><small>{new Date(entry.created_at).toLocaleString('es-MX')}</small></li>)}</ul>
    {cursor && <button type="button" disabled={busy} onClick={() => load(cursor)}>Ver anteriores</button>}
  </section>;
}
