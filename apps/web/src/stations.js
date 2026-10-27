/**
 * Una estación manda su reporte cada 30 s (device-agent, maybe_heartbeat).
 * Diez minutos sin reporte son unos veinte perdidos: ya no es un parpadeo de
 * la señal (#98). Es un valor por defecto, no una medición de campo.
 */
export const SIN_REPORTE_MIN = 10;

/** "reportando", "sin-reporte" o null si no hay fecha válida. Nunca afirma que siga conectada. */
export function stationStatus(device, now = Date.now(), minutes = SIN_REPORTE_MIN) {
  const seen = Date.parse(device.last_seen);
  if (!Number.isFinite(seen)) return null;
  return now - seen > minutes * 60000 ? "sin-reporte" : "reportando";
}

export function silentStations(devices, now = Date.now(), minutes = SIN_REPORTE_MIN) {
  return (devices || []).filter((d) => stationStatus(d, now, minutes) === "sin-reporte");
}
