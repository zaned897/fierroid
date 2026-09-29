import { isTestReading, orderedReadings } from "./readings.js";

export function trendReadings(rows, includeTests = false) {
  return orderedReadings(rows).filter((row) =>
    row.stable === true && Number.isFinite(row.weight_kg) && row.weight_kg >= 0 &&
    Number.isFinite(Date.parse(row.captured_at)) && (includeTests || !isTestReading(row)),
  ).reverse();
}
