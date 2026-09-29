import { useState } from "react";
import { chartPoints, trendReadings } from "./animalTrend.js";
import { capturedLabel, weightValue } from "./readings.js";

export default function EvolucionAnimal({ rows, hasMore }) {
  const [includeTests, setIncludeTests] = useState(false);
  const points = chartPoints(trendReadings(rows, includeTests));
  const minWeight = Math.min(...points.map((p) => p.weight_kg));
  const maxWeight = Math.max(...points.map((p) => p.weight_kg));
  return <section className="animal-trend" aria-label="Evolución del peso">
    <h3>Evolución del peso</h3>
    <p className="muted">{points.length} pesajes estables representados de {rows.length} cargados.
      {hasMore && " Hay pesajes anteriores: usa Ver más pesajes para ampliar la gráfica."}</p>
    <label className="animal-test-toggle"><input type="checkbox" checked={includeTests}
      onChange={(e) => setIncludeTests(e.target.checked)} /> Incluir lecturas de prueba</label>
    {includeTests && <p className="dashboard-warning">Incluye pesos de laboratorio o simulados; no representan necesariamente el peso real del animal.</p>}
    {points.length === 0 ? <p>No hay pesajes estables válidos para esta selección.{!includeTests && " Las lecturas de prueba están ocultas."}</p> : <>
      <svg className="animal-chart" viewBox="0 0 600 240" role="img" aria-label={`Evolución de ${points.length} pesajes estables. Detalle disponible en el historial inferior.`}>
        <line x1="54" y1="210" x2="550" y2="210" stroke="currentColor" />
        <line x1="54" y1="25" x2="54" y2="210" stroke="currentColor" />
        <text x="4" y="20">kg</text>
        <text x="4" y={minWeight === maxWeight ? "124" : "48"}>{weightValue(maxWeight)}</text>
        {minWeight !== maxWeight && <text x="4" y="202">{weightValue(minWeight)}</text>}
        {points.length > 1 && <polyline fill="none" stroke="currentColor" strokeWidth="2" points={points.map((p) => `${p.x},${p.y}`).join(" ")} />}
        {points.map((p) => <circle key={p.event_id} cx={p.x} cy={p.y} r="4" fill="currentColor"><title>{capturedLabel(p.captured_at)} · {weightValue(p.weight_kg)} kg · {p.device_id}</title></circle>)}
      </svg>
      <p className="muted">{capturedLabel(points[0].captured_at)} — {capturedLabel(points.at(-1).captured_at)}. Eje horizontal: fecha de captura.</p>
      {points.length === 1 && <p>Se necesita otro pesaje válido para mostrar una evolución.</p>}
    </>}
  </section>;
}
