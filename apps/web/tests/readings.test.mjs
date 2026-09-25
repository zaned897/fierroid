import assert from "node:assert/strict";
import test from "node:test";
import { orderedReadings, weightValue, isTestReading, capturedLabel } from "../src/readings.js";

test("ordena por captura, conserva pesajes distintos del mismo animal y deduplica por evento", () => {
  const newer = { event_id: "b", tag_id: "same", captured_at: "2026-09-25T18:00:00Z", weight_kg: 430 };
  const late = { event_id: "a", tag_id: "same", captured_at: "2026-09-24T18:00:00Z", received_at: "2026-09-25T19:00:00Z" };
  const tied = { ...newer, event_id: "c" };
  assert.deepEqual(orderedReadings([newer, late, newer, tied]).map((r) => r.event_id), ["c", "b", "a"]);
});

test("no transforma pesos ausentes en cero", () => {
  for (const value of [null, undefined, NaN, Infinity, ""]) assert.equal(weightValue(value), "—");
  assert.equal(weightValue(0), "0.0");
  assert.equal(weightValue(437.5), "437.5");
});

test("la procedencia de prueba depende del source y no de la organización", () => {
  assert.equal(isTestReading({ source: "mock" }), true);
  assert.equal(isTestReading({ source: "synthetic" }), true);
  assert.equal(isTestReading({ source: "serial", org: "pruebas" }), false);
  assert.equal(isTestReading({}), false);
  assert.equal(capturedLabel(null), "Fecha no disponible");
});
