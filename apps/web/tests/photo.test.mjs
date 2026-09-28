import assert from "node:assert/strict";
import test from "node:test";
import { reducirImagen } from "../src/photo.js";

test("corrige un JPEG llamado PNG sin modificar los bytes, incluso sin decodificador", async () => {
  const bytes = Uint8Array.from([0xff, 0xd8, 0xff, 0xe0, 0, 16]);
  const result = await reducirImagen(new File([bytes], "ejemplo.png", { type: "image/png" }));
  assert.equal(result.type, "image/jpeg");
  assert.equal(result.name, "foto.jpg");
  assert.deepEqual(new Uint8Array(await result.arrayBuffer()), bytes);
});

test("reconoce PNG y WebP aunque el MIME esté vacío o sea incorrecto", async () => {
  for (const [bytes, type] of [
    [[0x89, 0x50, 0x4e, 0x47, 13, 10, 26, 10], "image/png"],
    [[82, 73, 70, 70, 0, 0, 0, 0, 87, 69, 66, 80], "image/webp"],
  ]) {
    const result = await reducirImagen(new File([Uint8Array.from(bytes)], "foto.jpg"));
    assert.equal(result.type, type);
  }
});

test("no acepta texto ni una firma truncada por tener extensión de imagen", async () => {
  for (const bytes of ["no es una imagen", new Uint8Array([0xff, 0xd8])]) {
    await assert.rejects(reducirImagen(new File([bytes], "foto.png", { type: "image/png" })), /válida/);
  }
});
