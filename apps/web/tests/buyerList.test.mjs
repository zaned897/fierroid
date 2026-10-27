import assert from "node:assert/strict";
import test from "node:test";
import { buyerCsv, buyerRows, buyerSummary } from "../src/buyerList.js";
import { silentStations, stationStatus } from "../src/stations.js";

const r = (id, at, extra = {}) => ({ event_id: id, tag_id: `T${id}`, captured_at: at, weight_kg: 400, stable: true, source: "serial", device_id: "manga-1", ...extra });

test("la lista toma solo el rango, sin pruebas, del más antiguo al más reciente", () => {
  const rows = buyerRows([
    r("b", "2026-10-25T08:00:00Z"), r("a", "2026-10-25T07:00:00Z"), r("fuera", "2026-10-26T07:00:00Z"),
    r("sim", "2026-10-25T09:00:00Z", { source: "mock" }), r("sin", "2026-10-25T09:30:00Z", { weight_kg: null }),
  ], Date.parse("2026-10-25T00:00:00Z"), Date.parse("2026-10-26T00:00:00Z"));
  assert.deepEqual(rows.map((x) => x.event_id), ["a", "b"]);
});

test("el resumen suma solo pesos estables y cuenta las dudosas aparte", () => {
  const s = buyerSummary([r("a", "x", { weight_kg: 400 }), r("b", "x", { weight_kg: 450 }), r("c", "x", { weight_kg: 31, stable: false })]);
  assert.deepEqual(s, { pesajes: 3, animales: 3, totalKg: 850, promedioKg: 425, dudosas: 1 });
});

test("el CSV usa kg con punto, fecha UTC y escapa comas", () => {
  const csv = buyerCsv([r("a", "2026-10-25T07:00:00Z", { tag_id: "A,1", weight_kg: 437.5 })]);
  assert.equal(csv, 'arete,peso_kg,capturado_utc,estacion,estable\n"A,1",437.5,2026-10-25T07:00:00Z,manga-1,si\n');
});

test("una estación pasa a sin reporte tras el umbral y una fecha inválida no se juzga", () => {
  const now = Date.parse("2026-10-27T12:00:00Z");
  assert.equal(stationStatus({ last_seen: "2026-10-27T11:55:00Z" }, now), "reportando");
  assert.equal(stationStatus({ last_seen: "2026-10-27T11:40:00Z" }, now), "sin-reporte");
  assert.equal(stationStatus({ last_seen: null }, now), null);
  assert.deepEqual(silentStations([{ device_id: "a", last_seen: "2026-10-26T00:00:00Z" }, { device_id: "b", last_seen: "2026-10-27T11:59:00Z" }], now).map((d) => d.device_id), ["a"]);
});
