import assert from "node:assert/strict";
import test from "node:test";
import { config, firmar } from "../middleware.js";

const peticion = (h) => new Request("https://fierroid.vercel.app/v1/waitlist", { method: "POST", headers: h });

test("solo corre en la lista de espera", () => {
  assert.equal(config.matcher, "/v1/waitlist");
});

test("con secreto firma la IP real que pone Vercel", () => {
  const h = firmar(peticion({ "x-real-ip": "192.0.2.4" }), "s3creto");
  assert.equal(h.get("x-fierro-edge"), "s3creto");
  assert.equal(h.get("x-fierro-client-ip"), "192.0.2.4");
});

test("lo que inventa el cliente se descarta", () => {
  const h = firmar(peticion({ "x-real-ip": "192.0.2.4", "x-fierro-edge": "adivinado", "x-fierro-client-ip": "1.1.1.1" }), "s3creto");
  assert.equal(h.get("x-fierro-client-ip"), "192.0.2.4");
  const sin = firmar(peticion({ "x-fierro-edge": "adivinado", "x-fierro-client-ip": "1.1.1.1" }), "");
  assert.equal(sin.get("x-fierro-edge"), null);
  assert.equal(sin.get("x-fierro-client-ip"), null);
});
