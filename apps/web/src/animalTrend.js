import { isTestReading, orderedReadings } from "./readings.js";

export function trendReadings(rows, includeTests = false) {
  return orderedReadings(rows).filter((row) =>
    row.stable === true && Number.isFinite(row.weight_kg) && row.weight_kg >= 0 &&
    Number.isFinite(Date.parse(row.captured_at)) && (includeTests || !isTestReading(row)),
  ).reverse();
}

export function chartPoints(rows) {
  if (!rows.length) return [];
  const times = rows.map((r) => Date.parse(r.captured_at));
  const weights = rows.map((r) => r.weight_kg);
  const low = Math.min(...weights), high = Math.max(...weights);
  const start = Math.min(...times), end = Math.max(...times);
  return rows.map((row, i) => ({
    ...row,
    x: end === start ? 300 : 54 + (times[i] - start) / (end - start) * 492,
    y: high === low ? 120 : 200 - (weights[i] - low) / (high - low) * 160,
  }));
}
