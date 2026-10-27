import { apiFetch } from "./auth.js";

/**
 * Pesajes recientes página por página hasta cruzar `untilMs` o llegar a
 * `maxPages`. Dice si se cortó por el tope, para no presentar como completo
 * un hato que no se terminó de leer.
 */
export async function fetchReadingPages({ session, signal, deviceId, untilMs = -Infinity, maxPages = 10 }) {
  const readings = [];
  let cursor = null;
  for (let page = 0; page < maxPages; page += 1) {
    const query = new URLSearchParams({ limit: "200" });
    if (deviceId) query.set("device_id", deviceId);
    if (cursor) query.set("cursor", cursor);
    const body = await apiFetch(`/v1/readings?${query}`, { session, signal });
    readings.push(...(body.readings || []));
    cursor = body.next_cursor;
    const oldest = readings.at(-1);
    if (!cursor || (oldest && Date.parse(oldest.captured_at) < untilMs)) return { readings, truncated: false };
  }
  return { readings, truncated: Boolean(cursor) };
}
