import assert from "node:assert/strict";
import { test } from "node:test";
import { attachment, audioFormat, MAX_BYTES, uploadAttachments } from "../src/journalMedia.js";
import * as media from "../src/journalMedia.js";
import * as drafts from "../src/journalMediaDraft.js";

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
  let items = ["photo", "photo", "audio"].map((kind, index) => attachment(
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
  const update = (next) => { items = next; };
  await assert.rejects(uploadAttachments("nota", items, send, update), /ACK perdido/);
  assert.equal(stored.size, 2);
  assert.equal(items[0].status, "uploaded");
  assert.equal(items[1].status, "error");
  const result = await uploadAttachments("nota", items, send, update);
  assert.equal(stored.size, 3);
  assert.deepEqual(attempts, ["id-0", "id-1", "id-1", "id-2"]);
  assert.deepEqual(result.map((item) => item.attachment_id), items.map((item) => item.attachment_id));
});

test("los 4xx permanentes rechazan el adjunto y ningún reintento vuelve a enviarlo", async () => {
  for (let status = 400; status < 500; status++) {
    if ([401, 408, 429].includes(status)) continue;
    let items = [attachment(new Blob(["foto"]), "photo", [], "foto")];
    let calls = 0;
    const error = Object.assign(new Error("Rechazado"), { status });
    assert.equal(media.isPermanentRejection(error), true, `HTTP ${status}`);
    const send = async () => { calls++; throw error; };
    const update = (next) => { items = next; };
    await assert.rejects(uploadAttachments("nota", items, send, update));
    assert.equal(items[0].status, "rejected", `HTTP ${status}`);
    await assert.rejects(uploadAttachments("nota", items, send, update));
    assert.equal(calls, 1);
    assert.deepEqual(await uploadAttachments("nota", [], send), []);
  }
});

for (const error of [
  Object.assign(new Error("HTTP 401"), { status: 401 }),
  Object.assign(new Error("Sesión vencida sin status"), { unauthorized: true }),
  Object.assign(new Error("Sesión vencida con HTTP 401"), { status: 401, unauthorized: true }),
  Object.assign(new Error("HTTP 408"), { status: 408 }),
  Object.assign(new Error("HTTP 429"), { status: 429 }),
  Object.assign(new Error("HTTP 500"), { status: 500 }),
  Object.assign(new Error("HTTP 503"), { status: 503 }),
  new TypeError("Red"),
  new DOMException("Timeout", "AbortError"),
]) {
  test(`${error.message}: queda error y conserva bytes y UUID para reintentar`, async () => {
    const file = new Blob(["audio"]);
    let items = [attachment(file, "audio", [], "audio")];
    const update = (next) => { items = next; };
    await assert.rejects(uploadAttachments("nota", items, async () => { throw error; }, update),
      (caught) => caught === error);
    assert.equal(items[0].status, "error");
    assert.equal(media.isPermanentRejection(error), false);
    assert.equal(items[0].file, file);
    assert.equal(items[0].attachment_id, "audio");
    const result = await uploadAttachments("nota", items, async (_url, data) => {
      assert.equal(await data.get("file").text(), "audio");
      return { attachment_id: data.get("attachment_id") };
    }, update);
    assert.deepEqual(result, [{ attachment_id: "audio" }]);
    assert.equal(items[0].status, "uploaded");
  });
}

test("rechaza audio vacío o de menos de un segundo antes de adjuntarlo", () => {
  const file = new Blob(["cabecera sin audio"]);
  for (const duration of [0, 1, 100, 999, NaN, Infinity]) {
    assert.throws(() => media.audioAttachment(file, duration, [], "audio"), /segundo/);
  }
  assert.throws(() => media.audioAttachment(new Blob([]), 1500, [], "audio"), /segundo/);
  assert.equal(media.audioAttachment(file, 1000, [], "audio").duration_ms, 1000);
});

test("restaura solo blobs válidos y nunca deja una subida pendiente de una sesión anterior", () => {
  const file = new Blob(["foto"]);
  const item = { attachment_id: "id", kind: "photo", file };
  const restored = drafts.restoreMediaFiles([
    { ...item, status: "uploading" },
    { ...item, attachment_id: "rechazado", status: "rejected" },
    { ...item, attachment_id: "anterior" },
    { ...item, attachment_id: "sin-blob", status: "rejected", file: undefined },
    { ...item, attachment_id: "url", status: "uploading", file: "blob:ya-no-existe" },
    { ...item, attachment_id: "json", file: {} },
    { ...item, attachment_id: "vacio", file: new Blob([]) },
    null,
  ]);
  assert.deepEqual(restored.map(({ attachment_id, status }) => [attachment_id, status]), [
    ["id", "error"], ["rechazado", "rejected"], ["anterior", "pending"],
  ]);
  assert.equal(restored[0].file, file);
  assert.deepEqual(drafts.restoreMediaFiles({}), []);
});

test("restaurar conserva el ACK aunque falte el blob y rechaza audio corto con blob", async () => {
  const uploaded = { attachment_id: "ok", kind: "photo", status: "uploaded", result: { attachment_id: "ok" } };
  const restored = drafts.restoreMediaFiles([uploaded, {
    attachment_id: "corto", kind: "audio", file: new Blob(["cabecera"]), duration_ms: 10,
  }]);
  assert.equal(restored[1].status, "rejected");
  assert.deepEqual(await uploadAttachments("nota", [restored[0]], () => assert.fail("No reenviar un ACK")), [uploaded.result]);
});
