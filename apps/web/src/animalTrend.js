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
