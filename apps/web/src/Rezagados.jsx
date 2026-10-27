import { useCallback, useEffect, useRef, useState } from "react";
import { REZAGO, herdReview } from "./animalTrend.js";
import { fetchReadingPages } from "./readingPages.js";
import { capturedLabel, weightValue } from "./readings.js";
import "./funciones-panel.css";

const signed = (kg) => `${kg > 0 ? "+" : ""}${weightValue(kg)}`;

/** Animales que se quedan atrás (#95): la regla de la ficha, aplicada a todo el hato. */
export default function Rezagados({ session, onExpired, onAbrir }) {
  const [rows, setRows] = useState(null);
  const [truncated, setTruncated] = useState(false);
  const [error, setError] = useState(null);
  const [pesajes, setPesajes] = useState(REZAGO.pesajes);
  const request = useRef(null);

  const cargar = useCallback(async () => {
    request.current?.abort();
    const controller = new AbortController();
    request.current = controller;
    setError(null);
    try {
      const result = await fetchReadingPages({ session, signal: controller.signal });
      if (request.current !== controller) return;
      setRows(result.readings);
      setTruncated(result.truncated);
    } catch (err) {
      if (request.current !== controller) return;
      if (err.unauthorized) onExpired();
      else setError(err.name === "AbortError" ? "La consulta se canceló." : err.message);
    }
  }, [session, onExpired]);

  useEffect(() => {
    cargar();
    return () => { request.current?.abort(); request.current = null; };
  }, [cargar]);

  const review = rows ? herdReview(rows, { ...REZAGO, pesajes }) : null;

  return (
    <section className="panel rezagados" aria-labelledby="rezagados-titulo">
      <div className="row dashboard-card-heading">
        <h2 id="rezagados-titulo">Para revisar</h2>
        <label className="rezagados-regla">Sin ganar en
          <select value={pesajes} onChange={(e) => setPesajes(Number(e.target.value))}>
            {[2, 3, 4].map((n) => <option key={n} value={n}>{n} pesajes</option>)}
          </select>
        </label>
      </div>
      {error && <p className="error" role="alert">No se pudo revisar el hato. {error} <button type="button" onClick={cargar}>Reintentar</button></p>}
      {!review && !error && <p role="status">Revisando pesajes…</p>}
      {review && <>
        {review.behind.length === 0 && review.atypical.length === 0 &&
          <p>Ningún animal lleva {pesajes} pesajes seguidos sin ganar peso. {review.compared} animales con al menos dos días de pesaje.</p>}
        {review.behind.length > 0 && <>
          <p><strong>{review.behind.length} {review.behind.length === 1 ? "animal no ha" : "animales no han"} ganado peso</strong> en sus últimos {pesajes} pesajes.</p>
          <ul className="rezagados-lista">{review.behind.map((a) => <li key={a.tag_id}>
            <button type="button" onClick={() => onAbrir(a.tag_id)}>
              <span><span className="tag">{a.tag_id}</span><small>Último {weightValue(a.last.weight_kg)} kg, {capturedLabel(a.last.captured_at)}</small></span>
              <strong className="rezagados-alerta">{signed(a.stalledKg)} kg en {a.stalled} pesajes</strong>
            </button>
          </li>)}</ul>
        </>}
        {review.atypical.length > 0 && <>
          <p><strong>Último pesaje atípico:</strong> revisa si el animal se recargó o si había otro en la báscula. No cuenta para la ganancia.</p>
          <ul className="rezagados-lista">{review.atypical.map((a) => <li key={a.tag_id}>
            <button type="button" onClick={() => onAbrir(a.tag_id)}>
              <span><span className="tag">{a.tag_id}</span><small>{capturedLabel(a.atypical.captured_at)} · {a.atypical.device_id}</small></span>
              <strong className="rezagados-alerta">{weightValue(a.atypical.weight_kg)} kg</strong>
            </button>
          </li>)}</ul>
        </>}
        {review.restMedianKg !== null && <p className="muted">El resto del hato gana {signed(review.restMedianKg)} kg/día (mediana de {review.compared - review.behind.length} animales comparables).</p>}
        <p className="muted">"Sin ganar" es ganar {REZAGO.gananciaKg} kg o menos entre un pesaje y el siguiente. Cuenta un pesaje por día, sin lecturas de prueba, inestables ni atípicas.
          {truncated && " Solo se revisaron los 2,000 pesajes más recientes."}</p>
      </>}
    </section>
  );
}
