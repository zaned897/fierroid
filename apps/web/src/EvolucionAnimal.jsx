import { lazy, Suspense, useState } from "react";
import { trendReadings } from "./animalTrend.js";
import { capturedLabel } from "./readings.js";

const PesoChart = lazy(() => import("./PesoChart.jsx"));

export default function EvolucionAnimal({ rows, hasMore }) {
  const [includeTests, setIncludeTests] = useState(false);
  const [mode, setMode] = useState("line");
  const points = trendReadings(rows, includeTests);
  return <section className="animal-trend" aria-label="Evolución del peso">
    <h3>Evolución del peso</h3>
    <p className="muted">{points.length} pesajes estables representados de {rows.length} cargados.
      {hasMore && " Hay pesajes anteriores: usa Ver más pesajes para ampliar la gráfica."}</p>
    <label className="animal-test-toggle"><input type="checkbox" checked={includeTests}
      onChange={(e) => setIncludeTests(e.target.checked)} /> Incluir lecturas de prueba</label>
    {includeTests && <p className="dashboard-warning">Incluye pesos de laboratorio o simulados; no representan necesariamente el peso real del animal.</p>}
    {points.length === 0 ? <p>No hay pesajes estables válidos para esta selección.{!includeTests && " Las lecturas de prueba están ocultas."}</p> : <>
      <div className="chart-controls" role="group" aria-label="Tipo de gráfica">
        <button type="button" aria-pressed={mode === "line"} onClick={() => setMode("line")}>Línea</button>
        <button type="button" aria-pressed={mode === "points"} onClick={() => setMode("points")}>Puntos</button>
      </div>
      <Suspense fallback={<p role="status">Cargando gráfica…</p>}><PesoChart rows={points} mode={mode} /></Suspense>
      <p className="muted">Selecciona un punto para ver el pesaje. Con teclado, usa las flechas. El eje vertical se ajusta al rango de pesos.</p>
      <p className="muted">{capturedLabel(points[0].captured_at)} — {capturedLabel(points.at(-1).captured_at)}. Eje horizontal: fecha de captura.</p>
      {points.length === 1 && <p>Se necesita otro pesaje válido para mostrar una evolución.</p>}
    </>}
  </section>;
}
