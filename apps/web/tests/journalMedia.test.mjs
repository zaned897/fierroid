import assert from "node:assert/strict";
import { test } from "node:test";
import { attachment, audioFormat, MAX_BYTES, uploadAttachments } from "../src/journalMedia.js";

test("elige Opus y usa MP4 cuando el navegador lo requiere", () => {
  assert.equal(audioFormat({ isTypeSupported: () => true }), "audio/webm;codecs=opus");
  assert.equal(audioFormat({ isTypeSupported: (mime) => mime === "audio/mp4" }), "audio/mp4");
  assert.equal(audioFormat({}), null);
});

test("rechaza archivos vacíos, grandes y adjuntos que exceden el límite", () => {
  assert.throws(() => attachment(new Blob([]), "photo", [], "id"), /2 MB/);
  assert.throws(() => attachment(new Blob([new Uint8Array(MAX_BYTES + 1)]), "audio", [], "id"), /2 MB/);
  for (const [kind, total] of [["photo", 6], ["audio", 2]]) {
    assert.throws(() => attachment(new Blob(["x"]), kind,
      Array.from({ length: total }, () => ({ kind })), "id"), /hasta/);
  }
});

test("respuesta perdida a media subida conserva bytes e ids y se reintenta sin duplicar", async () => {
  const items = ["photo", "photo", "audio"].map((kind, index) => attachment(
    new Blob([`archivo ${index}`], { type: kind === "photo" ? "image/jpeg" : "audio/webm" }), kind, [], `id-${index}`,
  ));
  const stored = new Map();
  const attempts = [];
  let failed = false;
  async function send(path, data) {
    assert.equal(path, "/v1/journal/nota/attachments");
    const id = data.get("attachment_id");
    const raw = await data.get("file").text();
    attempts.push(id);
    if (stored.has(id)) assert.equal(stored.get(id), raw);
    stored.set(id, raw);
    if (id === "id-1" && !failed) { failed = true; throw new Error("ACK perdido"); }
    return { attachment_id: id };
  }
  await assert.rejects(uploadAttachments("nota", items, send), /ACK perdido/);
  assert.equal(stored.size, 2);
  const result = await uploadAttachments("nota", items, send);
  assert.equal(stored.size, 3);
  assert.deepEqual(attempts, ["id-0", "id-1", "id-0", "id-1", "id-2"]);
  assert.deepEqual(result.map((item) => item.attachment_id), items.map((item) => item.attachment_id));
});
