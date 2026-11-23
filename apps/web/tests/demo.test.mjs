import assert from "node:assert/strict";
import test from "node:test";
import { conDemo, demoActivo, demoInicial } from "../src/demo.js";

const user = { org: "los-encinos", demo_org: "los-encinos-demo" };

test("con el demo encendido, las rutas de datos van al rancho demo", () => {
  const session = { demo: true, user };
  assert.equal(conDemo("/v1/readings?limit=40", session), "/v1/readings?limit=40&org=los-encinos-demo");
  assert.equal(conDemo("/v1/animals", session), "/v1/animals?org=los-encinos-demo");
  assert.equal(conDemo("/v1/asistente", session), "/v1/asistente?org=los-encinos-demo");
});

test("no toca la sesión, rutas que ya dicen org, ni rutas fuera de la API", () => {
  const session = { demo: true, user };
  assert.equal(conDemo("/v1/auth/me", session), "/v1/auth/me");
  assert.equal(conDemo("/v1/animals/1/readings?org=x&limit=5", session), "/v1/animals/1/readings?org=x&limit=5");
  assert.equal(conDemo("/health", session), "/health");
});

test("apagado, o sin rancho demo, la ruta queda igual", () => {
  assert.equal(conDemo("/v1/readings", { demo: false, user }), "/v1/readings");
  assert.equal(conDemo("/v1/readings", { demo: true, user: { org: "x" } }), "/v1/readings");
  assert.equal(demoActivo({ demo: true, user: { org: "x", demo_org: null } }), false);
});

test("arranca en demo solo si la cuenta aún no tiene pesajes reales", () => {
  assert.equal(demoInicial(user, 0), true);
  assert.equal(demoInicial(user, 1), false);
  assert.equal(demoInicial({ org: "x" }, 0), false);
});
