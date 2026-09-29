import { useCallback, useEffect, useRef, useState } from "react";
import { apiFetch } from "./auth.js";
import { capturedLabel } from "./readings.js";

const categories = { observacion: "Observación", alimentacion: "Alimentación", manejo: "Manejo", salud: "Salud" };
function localNow() {
  const now = new Date();
  return new Date(now.getTime() - now.getTimezoneOffset() * 60000).toISOString().slice(0, 16);
}

export default function BitacoraAnimal({ animal, session, onExpired }) {
  const [entries, setEntries] = useState([]);
  const [cursor, setCursor] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);
  const [saved, setSaved] = useState(false);
  const [body, setBody] = useState("");
  const [category, setCategory] = useState("observacion");
  const [occurred, setOccurred] = useState(localNow);
  const request = useRef(null);
  const pending = useRef(null);
  const path = `/v1/animals/${encodeURIComponent(animal.tag_id)}/journal?org=${encodeURIComponent(animal.org)}`;

  const load = useCallback(async (next = null) => {
    if (request.current) return;
    const controller = new AbortController();
    request.current = controller;
    const timer = setTimeout(() => controller.abort(), 15000);
    setBusy(true);
    setError(null);
    try {
      const data = await apiFetch(`${path}&limit=20${next ? `&cursor=${encodeURIComponent(next)}` : ""}`, { session, signal: controller.signal });
      if (request.current !== controller) return;
      setEntries((prev) => [...new Map((next ? [...prev, ...data.entries] : data.entries).map((entry) => [entry.entry_id, entry])).values()]);
      setCursor(data.next_cursor);
    } catch (err) {
      if (request.current !== controller) return;
      if (err.unauthorized) onExpired();
      else {
        if (err.status === 403) { setEntries([]); setCursor(null); }
        setError(err.status === 404 ? "La bitácora aún no está disponible en esta API." : "No se pudo cargar la bitácora. Vuelve a intentar.");
      }
    } finally {
      clearTimeout(timer);
      if (request.current === controller) { request.current = null; setBusy(false); }
    }
  }, [path, session, onExpired]);

  useEffect(() => {
    load();
    return () => { const controller = request.current; request.current = null; controller?.abort(); };
  }, [load]);

  async function save(event) {
    event.preventDefault();
    if (request.current || !body.trim() || !Number.isFinite(Date.parse(occurred))) return;
    const content = { body: body.trim(), category, occurred_at: new Date(occurred).toISOString() };
    const fingerprint = JSON.stringify(content);
    if (pending.current?.fingerprint !== fingerprint) {
      pending.current = { fingerprint, entry_id: crypto.randomUUID() };
    }
    const controller = new AbortController();
    request.current = controller;
    const timer = setTimeout(() => controller.abort(), 15000);
    setBusy(true); setError(null); setSaved(false);
    try {
      await apiFetch(path, { session, method: "POST", signal: controller.signal,
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ ...content, entry_id: pending.current.entry_id }),
      });
      if (request.current !== controller) return;
      pending.current = null;
      setBody(""); setOccurred(localNow()); setSaved(true);
      request.current = null;
      await load();
    } catch (err) {
      if (request.current !== controller) return;
      if (err.unauthorized) onExpired();
      else setError("No se confirmó el guardado. Conservamos el texto: reintenta sin modificarlo para evitar duplicados.");
    } finally {
      clearTimeout(timer);
      if (request.current === controller) { request.current = null; setBusy(false); }
    }
  }

  return <section className="animal-journal" aria-label="Bitácora del animal">
    <div className="row"><h3>Bitácora</h3><button type="button" disabled={busy} onClick={() => load()}>Actualizar bitácora</button></div>
    <p className="muted">Registra eventos del animal. Las anotaciones se conservan; agrega otra para aclarar o corregir. Guarda antes de cerrar la ficha.</p>
    <form onSubmit={save}>
      <label className="campo">Fecha del evento (hora local)<input type="datetime-local" value={occurred} required disabled={busy} onChange={(e) => { setOccurred(e.target.value); setSaved(false); }} /></label>
      <label className="campo">Categoría<select value={category} disabled={busy} onChange={(e) => { setCategory(e.target.value); setSaved(false); }}>{Object.entries(categories).map(([key, label]) => <option key={key} value={key}>{label}</option>)}</select></label>
      <label className="campo">Anotación<textarea rows="3" maxLength={4000} required value={body} disabled={busy} onChange={(e) => { setBody(e.target.value); setSaved(false); }} /></label>
      <button type="submit" disabled={busy || !body.trim()}>Guardar anotación</button>
    </form>
    {busy && <p role="status">Procesando bitácora…</p>}
    {saved && <p role="status">Anotación guardada.</p>}
    {error && <p className="error" role="alert">{error}</p>}
    {!busy && !error && entries.length === 0 && <p>Todavía no hay anotaciones.</p>}
    <ol className="animal-history-list">{entries.map((entry) => <li key={entry.entry_id}>
      <strong>{categories[entry.category] || entry.category} · {capturedLabel(entry.occurred_at)}</strong>
      <p className="animal-journal-body">{entry.body}</p>
      <p className="muted">{entry.author} · Registrado: {capturedLabel(entry.created_at)}</p>
    </li>)}</ol>
    {cursor && <button type="button" disabled={busy} onClick={() => load(cursor)}>Ver anotaciones anteriores</button>}
  </section>;
}
