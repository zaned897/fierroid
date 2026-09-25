import { useEffect, useRef, useState } from "react";
import { apiFetch } from "./auth.js";
import { CowIcon } from "./icons/cows.jsx";
import { capturedLabel, isTestReading, orderedReadings, weightValue } from "./readings.js";
import usePanelResource from "./usePanelResource.js";

function ReadingFlags({ reading }) {
  return <>
    {reading.stable === false && <span className="dashboard-warning">Peso inestable</span>}
    {isTestReading(reading) && <span className="dashboard-test">Dato de prueba</span>}
  </>;
}

function ReadingTable({ readings }) {
  return (
    <table className="dashboard-readings">
      <thead><tr><th scope="col">Animal</th><th scope="col">Peso</th><th scope="col">Fecha y hora</th></tr></thead>
      <tbody>{readings.map((reading) => <tr key={reading.event_id}>
        <td><span className="dashboard-tag">{reading.tag_id || "Sin identificación"}</span><ReadingFlags reading={reading} /></td>
        <td className="dashboard-table-weight">{weightValue(reading.weight_kg)}{reading.weight_kg != null && " kg"}</td>
        <td><time dateTime={reading.captured_at}>{capturedLabel(reading.captured_at)}</time></td>
      </tr>)}</tbody>
    </table>
  );
}

export default function Pesajes({ session, onExpired, historial = false, onHistorial, onRecientes }) {
  const { data, error, busy, updatedAt, refresh } = usePanelResource(
    `/v1/readings?limit=${historial ? 40 : 5}`, session, onExpired, historial ? 0 : 30000,
  );
  const [older, setOlder] = useState([]);
  const [nextCursor, setNextCursor] = useState(undefined);
  const [pageError, setPageError] = useState(null);
  const [pageDenied, setPageDenied] = useState(false);
  const [loadingMore, setLoadingMore] = useState(false);
  const pageRequest = useRef(null);
  const readings = data && !pageDenied ? orderedReadings([...(data.readings || []), ...older]) : [];
  const latest = readings[0];
  const cursor = nextCursor === undefined ? data?.next_cursor : nextCursor;

  useEffect(() => () => {
    pageRequest.current?.abort();
    pageRequest.current = null;
  }, []);

  const loadMore = async () => {
    if (!cursor || pageRequest.current) return;
    const controller = new AbortController();
    pageRequest.current = controller;
    setLoadingMore(true);
    setPageError(null);
    const timeout = setTimeout(() => controller.abort(), 15000);
    try {
      const body = await apiFetch(`/v1/readings?limit=40&cursor=${encodeURIComponent(cursor)}`, { session, signal: controller.signal });
      if (pageRequest.current !== controller) return;
      setOlder((previous) => orderedReadings([...previous, ...(body.readings || [])]));
      setNextCursor(body.next_cursor || null);
    } catch (err) {
      if (pageRequest.current !== controller) return;
      if (err.unauthorized) onExpired();
      else {
        if (err.status === 403) setPageDenied(true);
        setPageError(err.name === "AbortError" ? "La consulta tardó demasiado. Vuelve a intentar." : err.message);
      }
    } finally {
      clearTimeout(timeout);
      if (pageRequest.current === controller) {
        pageRequest.current = null;
        setLoadingMore(false);
      }
    }
  };

  return <>
    <div className="dashboard-reading-status">
      <span className={error ? "error" : "muted"}>
        {error ? "No se pudo actualizar" : updatedAt ? `${historial ? "Historial consultado" : "Última consulta"}: ${updatedAt.toLocaleTimeString("es-MX", { hourCycle: "h23" })}` : "Consultando pesajes…"}
      </span>
      <span className="muted">Hora de este dispositivo</span>
    </div>
    {error && <div className="dashboard-error" role="alert"><strong>{data ? "Mostrando la última información disponible." : "No pudimos cargar los pesajes."}</strong><p>{error}</p><button type="button" onClick={refresh} disabled={busy}>Reintentar</button></div>}
    {!data && !error && <div className="panel dashboard-empty" role="status">Cargando pesajes…</div>}
    {pageError && <p className="error" role="alert">{pageError}</p>}
    {data && !latest && !pageDenied && <section className="panel dashboard-empty"><CowIcon size={48} /><h2>Aún no hay pesajes</h2><p>Los pesajes aparecerán aquí cuando el equipo los envíe.</p><button type="button" onClick={refresh} disabled={busy}>Actualizar</button></section>}
    {latest && <>
      {!historial && <section className="panel dashboard-latest" aria-label="Último pesaje">
        <h2>Último pesaje</h2>
        <div className="dashboard-latest-body">
          <div><div className="dashboard-weight">{weightValue(latest.weight_kg)}{latest.weight_kg != null && <span>kg</span>}</div><p className="dashboard-animal-id">Animal {latest.tag_id || "sin identificación"}</p></div>
          <div className="dashboard-capture"><time dateTime={latest.captured_at}>{capturedLabel(latest.captured_at)}</time>{latest.stable === true && <span className="muted">Peso estable</span>}<ReadingFlags reading={latest} /></div>
        </div>
      </section>}
      <section className="panel" aria-label={historial ? "Historial de pesajes" : "Lecturas recientes"}>
        <div className="row dashboard-card-heading"><h2>{historial ? "Pesajes registrados" : "Lecturas recientes"}</h2>
          {historial ? <button type="button" className="dashboard-text-button" onClick={onRecientes}>Ver recientes →</button> : <button type="button" className="dashboard-text-button" onClick={refresh} disabled={busy}>{busy ? "Actualizando…" : "Actualizar"}</button>}
        </div>
        <ReadingTable readings={historial ? readings : readings.slice(0, 5)} />
        {historial && cursor && <button type="button" className="mas" onClick={loadMore} disabled={loadingMore}>{loadingMore ? "Cargando…" : "Ver más antiguas"}</button>}
        {!historial && <button type="button" className="dashboard-text-button dashboard-history-link" onClick={onHistorial}>Ver historial →</button>}
      </section>
    </>}
  </>;
}
