import assert from "node:assert/strict";
import test from "node:test";
import { hiddenTestCount, outlierIds, trendReadings, trendSummary } from "../src/animalTrend.js";

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
test("cuenta las pruebas ocultas para que el estado vacío no parezca un error", () => {
  const readings = [row("sim","2026-09-01",{source:"proto-sim"}), row("syn","2026-09-02",{source:"synthetic"}), row("inestable","2026-09-03",{source:"mock",stable:false})];
  assert.equal(trendReadings(readings).length,0);
  assert.equal(hiddenTestCount(readings),2);
  assert.equal(hiddenTestCount([row("real","2026-09-01")]),0);
});
test("resume cambio y ganancia diaria entre el primer y el último pesaje", () => {
  assert.equal(trendSummary([row("a","2026-09-01")]),null);
  const s = trendSummary([row("a","2026-09-01T00:00:00Z",{weight_kg:400}), row("b","2026-09-11T00:00:00Z",{weight_kg:412})]);
  assert.deepEqual(s,{deltaKg:12, days:10, dailyKg:1.2});
  assert.equal(trendSummary([row("a","2026-09-01T08:00:00Z"), row("b","2026-09-01T12:00:00Z",{weight_kg:401})]).dailyKg,null);
});
test("señala el pesaje que se aparta de sus vecinos sin tocar la tendencia normal", () => {
  const kg = [400, 405, 410, 480, 420, 425, 430];
  const points = kg.map((w, i) => row(`p${i}`, `2026-09-${String(i + 1).padStart(2, "0")}`, {weight_kg:w}));
  assert.deepEqual([...outlierIds(points)], ["p3"]);
  const growth = [200, 215, 230, 245, 260, 275].map((w, i) => row(`g${i}`, `2026-09-${String(i + 1).padStart(2, "0")}`, {weight_kg:w}));
  assert.equal(outlierIds(growth).size, 0);
  assert.equal(outlierIds(points.slice(0, 3)).size, 0);
});

test("un animal se queda atrás tras dos pesajes seguidos ganando 1 kg o menos, y un repeso del mismo día no cuenta", async () => {
  const { herdReview, stalledCount } = await import("../src/animalTrend.js");
  const serie = (tag, kgs) => kgs.map((w, i) => row(`${tag}${i}`, `2026-09-${String(i * 7 + 1).padStart(2, "0")}T10:00:00Z`, {weight_kg:w, tag_id:tag}));
  const parado = serie("A", [400, 410, 409, 409.5]);
  const crece = serie("B", [400, 407, 414, 421]);
  const repeso = [...serie("C", [400, 407]), row("C-rep", "2026-09-08T12:00:00Z", {weight_kg:406, tag_id:"C"})];
  assert.equal(stalledCount(trendReadings(parado)), 2);
  assert.equal(stalledCount(trendReadings(repeso)), 0);
  const review = herdReview([...parado, ...crece, ...repeso]);
  assert.deepEqual(review.behind.map((a) => [a.tag_id, a.stalledKg]), [["A", -0.5]]);
  assert.equal(review.compared, 3);
  assert.equal(herdReview([...parado, ...crece], { pesajes: 3, gananciaKg: 1 }).behind.length, 0);
  assert.equal(herdReview([...crece]).restMedianKg, 1);
});

test("un solo pesaje no basta para juzgar, y un atípico al final se señala aparte", async () => {
  const { herdReview } = await import("../src/animalTrend.js");
  const unico = [row("u0", "2026-09-01", {tag_id:"U"})];
  const kg = [400, 405, 410, 415, 420, 425, 495];
  const salto = kg.map((w, i) => row(`s${i}`, `2026-09-${String(i + 1).padStart(2, "0")}`, {weight_kg:w, tag_id:"S"}));
  const review = herdReview([...unico, ...salto]);
  assert.equal(review.compared, 1);
  assert.deepEqual(review.atypical.map((a) => a.tag_id), ["S"]);
  assert.deepEqual(review.behind, []);
});
