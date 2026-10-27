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

/**
 * Regla de "se quedó atrás" (#95): tantos pesajes seguidos ganando 1 kg o
 * menos entre uno y otro. El kilo absorbe el ruido de la báscula. Es un punto
 * de partida, no un dato zootécnico; el panel deja cambiar los pesajes.
 */
export const REZAGO = { pesajes: 2, gananciaKg: 1 };

const dayKey = (p) => p.captured_at.slice(0, 10);

/** El último pesaje de cada día: pasar dos veces por la báscula el mismo día no es "no ganar". */
function lastPerDay(points) {
  return [...new Map(points.map((p) => [dayKey(p), p])).values()];
}

/** Cuántos intervalos seguidos, contando desde el último, ganaron gananciaKg o menos. */
export function stalledCount(points, gananciaKg = REZAGO.gananciaKg) {
  const days = lastPerDay(points);
  let count = 0;
  for (let i = days.length - 1; i > 0; i -= 1) {
    if (days[i].weight_kg - days[i - 1].weight_kg > gananciaKg) break;
    count += 1;
  }
  return count;
}

/**
 * Revisión del hato con las mismas reglas de la ficha: sin pruebas, sin
 * inestables y sin atípicos en la ganancia. Agrupa por arete; la API no
 * manda la organización en cada pesaje, así que un superusuario que mezcla
 * ranchos ve aretes repetidos como un solo animal.
 */
export function herdReview(rows, rule = REZAGO) {
  const byTag = new Map();
  for (const row of rows) {
    if (!row.tag_id) continue;
    byTag.set(row.tag_id, [...(byTag.get(row.tag_id) || []), row]);
  }
  const animals = [...byTag].map(([tag, readings]) => {
    const points = trendReadings(readings);
    const outliers = outlierIds(points);
    const clean = points.filter((p) => !outliers.has(p.event_id));
    const days = lastPerDay(clean);
    const stalled = stalledCount(clean, rule.gananciaKg);
    return {
      tag_id: tag,
      last: clean.at(-1) || null,
      stalledKg: stalled ? days.at(-1).weight_kg - days.at(-1 - stalled).weight_kg : null,
      dailyKg: trendSummary(clean)?.dailyKg ?? null,
      stalled,
      atypical: points.length > 0 && outliers.has(points.at(-1).event_id) ? points.at(-1) : null,
      comparable: days.length >= 2,
    };
  });
  const behind = animals.filter((a) => a.comparable && a.stalled >= rule.pesajes)
    .sort((a, b) => b.stalled - a.stalled || a.stalledKg - b.stalledKg);
  const behindTags = new Set(behind.map((a) => a.tag_id));
  const rest = animals.filter((a) => a.comparable && !behindTags.has(a.tag_id) && a.dailyKg !== null);
  return {
    behind,
    atypical: animals.filter((a) => a.atypical),
    compared: animals.filter((a) => a.comparable).length,
    restMedianKg: rest.length ? median(rest.map((a) => a.dailyKg)) : null,
  };
}
