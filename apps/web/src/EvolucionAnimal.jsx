import { lazy, Suspense, useState } from "react";
import { hiddenTestCount, outlierIds, trendReadings, trendSummary } from "./animalTrend.js";
import { capturedLabel, weightValue } from "./readings.js";

const PesoChart = lazy(() => import("./PesoChart.jsx"));

export default function EvolucionAnimal({ rows, hasMore }) {
  const [includeTests, setIncludeTests] = useState(false);
  const [mode, setMode] = useState("line");
  const points = trendReadings(rows, includeTests);
  const hiddenTests = includeTests ? 0 : hiddenTestCount(rows);
  const outliers = outlierIds(points);
  const flagged = points.filter((p) => outliers.has(p.event_id));
  // Un atípico no debe mover la ganancia diaria: el resumen usa solo la tendencia.
  const summary = trendSummary(points.filter((p) => !outliers.has(p.event_id)));
  const signed = (kg) => `${kg > 0 ? "+" : ""}${weightValue(kg)}`;
  return <section className="animal-trend" aria-label="Evolución del peso">
    <h3>Evolución del peso</h3>
    <p className="muted">{points.length} pesajes estables representados de {rows.length} cargados.
      {hasMore && " Hay pesajes anteriores: usa Ver más pesajes para ampliar la gráfica."}</p>
    <label className="animal-test-toggle"><input type="checkbox" checked={includeTests}
      onChange={(e) => setIncludeTests(e.target.checked)} /> Incluir lecturas de prueba</label>
    {includeTests && <p className="dashboard-warning">Incluye pesos de laboratorio o simulados; no representan necesariamente el peso real del animal. Se dibujan en ámbar.</p>}
    {points.length === 0 ? <div className="animal-trend-empty">
      <p>No hay pesajes estables válidos para esta selección.</p>
      {hiddenTests > 0 && <>
        <p>Hay {hiddenTests} pesajes de prueba ocultos (simulador o prototipo).</p>
        <button type="button" onClick={() => setIncludeTests(true)}>Mostrar lecturas de prueba</button>
      </>}
    </div> : <>
      {summary && <dl className="trend-summary">
        <div><dt>Último peso</dt><dd>{weightValue(points.at(-1).weight_kg)} kg</dd></div>
        <div><dt>Cambio</dt><dd>{signed(summary.deltaKg)} kg</dd></div>
        <div><dt>Ganancia diaria</dt><dd>{summary.dailyKg === null ? "—" : `${signed(summary.dailyKg)} kg/día`}</dd></div>
      </dl>}
      <div className="chart-controls" role="group" aria-label="Tipo de gráfica">
        <button type="button" aria-pressed={mode === "line"} onClick={() => setMode("line")}>Línea</button>
        <button type="button" aria-pressed={mode === "points"} onClick={() => setMode("points")}>Puntos</button>
      </div>
      <Suspense fallback={<p role="status">Cargando gráfica…</p>}><PesoChart rows={points} mode={mode} outliers={outliers} /></Suspense>
      {flagged.length > 0 && <div className="trend-outliers" role="note">
        <p><strong>{flagged.length} {flagged.length === 1 ? "lectura atípica" : "lecturas atípicas"}</strong> (en rojo): se apartan de los pesajes vecinos. Revisa si el animal se recargó o si había otro en la báscula. No cuentan para la ganancia diaria.</p>
        <ul>{flagged.map((p) => <li key={p.event_id}>{capturedLabel(p.captured_at)}: {weightValue(p.weight_kg)} kg · {p.device_id}</li>)}</ul>
      </div>}
      <p className="muted">Selecciona un punto para ver el pesaje. Con teclado, usa las flechas. El eje vertical se ajusta al rango de pesos.</p>
      <p className="muted">{capturedLabel(points[0].captured_at)} — {capturedLabel(points.at(-1).captured_at)}. Eje horizontal: fecha de captura.</p>
      {points.length === 1 && <p>Se necesita otro pesaje válido para mostrar una evolución.</p>}
    </>}
  </section>;
}
