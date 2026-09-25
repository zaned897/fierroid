/** Mantener event_id: un animal puede tener varios pesajes legítimos. */
export function orderedReadings(readings) {
  return [...new Map(readings.map((r) => [r.event_id, r])).values()].sort((a, b) =>
    Date.parse(b.captured_at) - Date.parse(a.captured_at) || b.event_id.localeCompare(a.event_id),
  );
}

export function weightValue(kg) {
  return typeof kg === "number" && Number.isFinite(kg) ? kg.toFixed(1) : "—";
}

export function capturedLabel(iso) {
  if (!iso || !Number.isFinite(Date.parse(iso))) return "Fecha no disponible";
  return new Date(iso).toLocaleString("es-MX", {
    day: "numeric", month: "short", year: "numeric", hour: "2-digit", minute: "2-digit", hourCycle: "h23",
  });
}

export function isTestReading(reading) {
  return ["mock", "synthetic"].includes(reading.source);
}
