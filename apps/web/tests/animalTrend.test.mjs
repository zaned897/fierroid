import assert from "node:assert/strict";
import test from "node:test";
import { trendReadings } from "../src/animalTrend.js";

const row = (id, date, extra = {}) => ({event_id:id, captured_at:date, weight_kg:400, stable:true, source:"serial", ...extra});
test("la curva excluye pruebas, pesos inestables, ausentes y fechas inválidas", () => {
  const readings = [row("real","2026-09-01"), ...["mock","synthetic","proto-rc522"].map((source) => row(source,"2026-09-02",{source})), row("unstable","2026-09-03",{stable:false}), row("missing","2026-09-04",{weight_kg:null}), row("date","bad")];
  assert.deepEqual(trendReadings(readings).map((r)=>r.event_id),["real"]);
  assert.equal(trendReadings(readings,true).length,4);
});
test("ordena por captura, deduplica evento y conserva lecturas distintas del mismo día", () => {
  const first=row("a","2026-09-01");
  const late=row("b","2026-08-31",{received_at:"2026-09-05"});
  assert.deepEqual(trendReadings([first,late,first,row("c","2026-09-01")]).map((r)=>r.event_id),["b","a","c"]);
});
