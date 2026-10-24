import { isTestReading, orderedReadings } from "./readings.js";

const DAY_MS = 86400000;

export function trendReadings(rows, includeTests = false) {
  return orderedReadings(rows).filter((row) =>
    row.stable === true && Number.isFinite(row.weight_kg) && row.weight_kg >= 0 &&
    Number.isFinite(Date.parse(row.captured_at)) && (includeTests || !isTestReading(row)),
  ).reverse();
}

/** Pruebas que la gráfica ocultaría por defecto: el estado vacío debe decirlo. */
export function hiddenTestCount(rows) {
  return trendReadings(rows, true).length - trendReadings(rows).length;
}

/** Cambio entre el primer y el último punto; ganancia diaria solo con al menos un día de por medio. */
export function trendSummary(points) {
  if (points.length < 2) return null;
  const first = points[0];
  const last = points.at(-1);
  const days = (Date.parse(last.captured_at) - Date.parse(first.captured_at)) / DAY_MS;
  const deltaKg = last.weight_kg - first.weight_kg;
  return { deltaKg, days, dailyKg: days >= 1 ? deltaKg / days : null };
}

const median = (values) => {
  const sorted = [...values].sort((a, b) => a - b);
  const mid = sorted.length >> 1;
  return sorted.length % 2 ? sorted[mid] : (sorted[mid - 1] + sorted[mid]) / 2;
};

/**
 * Pesajes que se apartan de sus vecinos: animal recargado en la manga, dos
 * animales en la báscula, arete mal leído. Se señalan, nunca se borran.
 * La pendiente de toda la serie (mediana de pendientes entre pares, robusta a
 * los propios atípicos) proyecta desde hasta 3 vecinos por lado el peso
 * esperado: así un becerro que crece rápido no parece atípico en los extremos.
 * Con menos de 3 vecinos no hay base para juzgar.
 */
export function outlierIds(points, window = 3) {
  const ids = new Set();
  const day = (p) => Date.parse(p.captured_at) / DAY_MS;
  const slopes = points.flatMap((a, j) => points.slice(j + 1)
    .filter((b) => day(b) !== day(a))
    .map((b) => (b.weight_kg - a.weight_kg) / (day(b) - day(a))));
  const slope = slopes.length ? median(slopes) : 0;
  points.forEach((point, i) => {
    const neighbors = [...points.slice(Math.max(0, i - window), i), ...points.slice(i + 1, i + 1 + window)];
    if (neighbors.length < 3) return;
    const expected = median(neighbors.map((n) => n.weight_kg + slope * (day(point) - day(n))));
    if (Math.abs(point.weight_kg - expected) > Math.max(15, expected * 0.07)) ids.add(point.event_id);
  });
  return ids;
}
