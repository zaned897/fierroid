import { isTestReading, orderedReadings } from "./readings.js";

/**
 * Lista para el comprador (#99): los pesajes de un rango, del más antiguo al
 * más reciente. Las lecturas dudosas se quedan y se marcan; las de prueba no
 * son ganado y no entran.
 */
export function buyerRows(readings, fromMs, toMs) {
  return orderedReadings(readings)
    .filter((r) => !isTestReading(r) && Number.isFinite(r.weight_kg))
    .filter((r) => {
      const t = Date.parse(r.captured_at);
      return t >= fromMs && t < toMs;
    })
    .reverse();
}

/** Totales con los pesos estables; los inestables se cuentan aparte. */
export function buyerSummary(rows) {
  const stable = rows.filter((r) => r.stable === true);
  const total = stable.reduce((sum, r) => sum + r.weight_kg, 0);
  return {
    pesajes: rows.length,
    animales: new Set(rows.map((r) => r.tag_id || "")).size,
    totalKg: total,
    promedioKg: stable.length ? total / stable.length : null,
    dudosas: rows.length - stable.length,
  };
}

const csvCell = (value) => {
  const text = String(value ?? "");
  return /[",\n]/.test(text) ? `"${text.replaceAll('"', '""')}"` : text;
};

/** CSV neutro: kg con punto decimal y fecha ISO UTC, como el contrato de datos. */
export function buyerCsv(rows) {
  const header = ["arete", "peso_kg", "capturado_utc", "estacion", "estable"];
  const lines = rows.map((r) => [r.tag_id, r.weight_kg.toFixed(1), r.captured_at, r.device_id, r.stable === true ? "si" : "no"]);
  return [header, ...lines].map((line) => line.map(csvCell).join(",")).join("\n") + "\n";
}
