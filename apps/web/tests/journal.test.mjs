import assert from "node:assert/strict";
import test from "node:test";
import { diaryDraftKey, draftKey, clearAllDrafts, loadDraft, saveDraft } from "../src/bitacoraDraft.js";
import { journalPath, journalQuestion, localDay } from "../src/journal.js";

test("un día local conserva medianoche y su límite exclusivo incluso con cambio de horario", () => {
  const original = process.env.TZ;
  process.env.TZ = "America/New_York";
  try {
    const params = new URL(journalPath("rancho", { from: "2026-03-08", to: "2026-03-08" }), "http://localhost").searchParams;
    assert.equal(params.get("desde"), "2026-03-08T05:00:00.000Z");
    assert.equal(params.get("hasta"), "2026-03-09T04:00:00.000Z");
    assert.equal(localDay("2026-03-08T04:30:00.000Z"), "2026-03-07");
  } finally {
    if (original === undefined) delete process.env.TZ;
    else process.env.TZ = original;
  }
});

test("la consulta conserva organización y arete completo como parámetros", () => {
  const params = new URL(journalPath("mi rancho", { tag: "proto:00/01" }), "http://localhost").searchParams;
  assert.equal(params.get("org"), "mi rancho");
  assert.equal(params.get("tag"), "proto:00/01");
  assert.equal(params.has("desde"), false);
  assert.equal(params.has("hasta"), false);
});

test("el borrador del diario se aísla por cuenta y organización y se limpia al salir", () => {
  const values = new Map();
  const storage = {
    get length() { return values.size; },
    key: (index) => [...values.keys()][index],
    getItem: (key) => values.get(key) ?? null,
    setItem: (key, value) => values.set(key, value),
    removeItem: (key) => values.delete(key),
  };
  const user = { email: "ana@example.test" };
  const key = diaryDraftKey(user, "norte");
  saveDraft(key, { body: "Revisión.", animals: ["001", "002"], entry_id: "mismo-uuid" }, { storage });
  assert.deepEqual(loadDraft(key, { storage }).draft.animals, ["001", "002"]);
  assert.equal(loadDraft(diaryDraftKey(user, "sur"), { storage }).draft, null);
  assert.equal(loadDraft(diaryDraftKey({ email: "otra@example.test" }, "norte"), { storage }).draft, null);
  assert.equal(loadDraft(draftKey(user, { org: "norte", tag_id: "diario" }), { storage }).draft, null);
  clearAllDrafts({ storage });
  assert.equal(values.size, 0);
});

test("el acceso al asistente redacta la pregunta con animal y periodo", () => {
  assert.equal(journalQuestion({ tag: "001", from: "2026-11-18", to: "2026-11-19" }),
    "¿Qué información tienes del animal con arete 001 desde el 2026-11-18 hasta el 2026-11-19?");
  assert.equal(journalQuestion({}), "¿Qué información tienes de mi rancho?");
});
