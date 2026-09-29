import { useCallback, useEffect, useRef, useState } from "react";
import { apiFetch } from "./auth.js";
import EvolucionAnimal from "./EvolucionAnimal.jsx";
import { capturedLabel, isTestReading, orderedReadings, weightValue } from "./readings.js";

export default function HistorialAnimal({ animal, session, onExpired }) {
  const [rows, setRows] = useState([]);
  const [cursor, setCursor] = useState(null);
  const [busy, setBusy] = useState(true);
  const [error, setError] = useState(null);
  const request = useRef(null);

  const cargar = useCallback(async (siguiente = null) => {
    if (request.current) return;
    const controller = new AbortController();
    request.current = controller;
    const timeout = setTimeout(() => controller.abort(), 15000);
    setBusy(true);
    setError(null);
    try {
      const query = new URLSearchParams({ org: animal.org, limit: "20" });
      if (siguiente) query.set("cursor", siguiente);
      const body = await apiFetch(`/v1/animals/${encodeURIComponent(animal.tag_id)}/readings?${query}`, {
        session, signal: controller.signal,
      });
      if (request.current !== controller) return;
      setRows((prev) => orderedReadings(siguiente ? [...prev, ...body.readings] : body.readings));
      setCursor(body.next_cursor);
    } catch (err) {
      if (request.current !== controller) return;
      if (err.unauthorized) onExpired();
      else {
        if (err.status === 403) { setRows([]); setCursor(null); }
        setError(err.status === 404 ? "El historial aún no está disponible en esta API." :
          err.name === "AbortError" ? "La consulta tardó demasiado. Vuelve a intentar." : err.message);
      }
    } finally {
      clearTimeout(timeout);
      if (request.current === controller) { request.current = null; setBusy(false); }
    }
  }, [animal.org, animal.tag_id, session, onExpired]);

  useEffect(() => {
    cargar();
    return () => {
      const controller = request.current;
      request.current = null;
      controller?.abort();
    };
  }, [cargar]);

  return <section className="animal-history" aria-label="Historial de pesajes del animal">
    <div className="row"><h3>Historial de pesajes</h3>
      <button type="button" disabled={busy} onClick={() => cargar()}>Actualizar historial</button></div>
    <p className="muted">Fechas en tu hora local. La estación indica dónde se capturó cada pesaje.</p>
    {error && <p className="error" role="alert">{error}</p>}
    {busy && <p role="status">Cargando pesajes…</p>}
    {!busy && !error && rows.length === 0 && <p>Este animal todavía no tiene pesajes.</p>}
    {rows.length > 0 && <EvolucionAnimal rows={rows} hasMore={Boolean(cursor)} />}
    <ol className="animal-history-list">{rows.map((row) => <li key={row.event_id}>
      <strong>{weightValue(row.weight_kg)} kg</strong>
      <dl><dt>Capturado</dt><dd>{capturedLabel(row.captured_at)}</dd>
        <dt>Recibido</dt><dd>{capturedLabel(row.received_at)}</dd>
        <dt>Estación</dt><dd>{row.device_id}</dd></dl>
      {row.stable === false && <span className="dashboard-warning">Peso inestable</span>}
      {isTestReading(row) && <span className="dashboard-test">Lectura de prueba</span>}
    </li>)}</ol>
    {cursor && <button type="button" disabled={busy} onClick={() => cargar(cursor)}>Ver más pesajes</button>}
  </section>;
}
