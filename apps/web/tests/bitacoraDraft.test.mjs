import assert from "node:assert/strict";
import test from "node:test";
import { VIGENCIA_MS, clearAllDrafts, clearDraft, draftKey, loadDraft, saveDraft } from "../src/bitacoraDraft.js";

function memoria() {
  const m = new Map();
  return {
    get length() { return m.size; },
    key: (i) => [...m.keys()][i] ?? null,
    getItem: (k) => (m.has(k) ? m.get(k) : null),
    setItem: (k, v) => m.set(k, String(v)),
    removeItem: (k) => m.delete(k),
    _m: m,
  };
}
const bloqueado = {
  get length() { throw new Error("SecurityError"); },
  key() { throw new Error("SecurityError"); },
  getItem() { throw new Error("SecurityError"); },
  setItem() { throw new Error("SecurityError"); },
  removeItem() { throw new Error("SecurityError"); },
};

const ana = { email: "ana@rancho.mx" };
const vaca = { org: "los-encinos", tag_id: "484111000001" };
const borrador = { body: "Cojea de la pata trasera", category: "salud", occurred: "2026-11-09T08:00", entry_id: "6f1c-uuid", fingerprint: "{}" };

test("recargar restaura el texto y el mismo UUID", () => {
  const storage = memoria();
  const key = draftKey(ana, vaca);
  assert.equal(saveDraft(key, borrador, { storage, now: 1000 }), true);
  const { draft, disponible } = loadDraft(key, { storage, now: 2000 });
  assert.equal(disponible, true);
  assert.equal(draft.body, borrador.body);
  assert.equal(draft.entry_id, "6f1c-uuid");
});

test("otro usuario, otra organización u otro animal no ven el borrador", () => {
  const storage = memoria();
  saveDraft(draftKey(ana, vaca), borrador, { storage, now: 1000 });
  for (const [u, a] of [
    [{ email: "beto@rancho.mx" }, vaca],
    [ana, { ...vaca, org: "valle-verde" }],
    [ana, { ...vaca, tag_id: "484111000002" }],
  ]) {
    assert.equal(loadDraft(draftKey(u, a), { storage, now: 2000 }).draft, null);
  }
});

test("sin usuario no hay clave ni borrador", () => {
  assert.equal(draftKey(null, vaca), null);
  assert.equal(saveDraft(null, borrador, { storage: memoria() }), false);
});

test("un borrador vencido se descarta", () => {
  const storage = memoria();
  const key = draftKey(ana, vaca);
  saveDraft(key, borrador, { storage, now: 0 });
  assert.equal(loadDraft(key, { storage, now: VIGENCIA_MS + 1 }).draft, null);
  assert.equal(storage.getItem(key), null);
});

test("confirmación limpia el borrador", () => {
  const storage = memoria();
  const key = draftKey(ana, vaca);
  saveDraft(key, borrador, { storage });
  clearDraft(key, { storage });
  assert.equal(loadDraft(key, { storage }).draft, null);
});

test("cerrar sesión borra todos los borradores y nada más", () => {
  const storage = memoria();
  storage.setItem("fierro.session", "{}");
  saveDraft(draftKey(ana, vaca), borrador, { storage });
  saveDraft(draftKey(ana, { ...vaca, tag_id: "2" }), borrador, { storage });
  clearAllDrafts({ storage });
  assert.deepEqual([...storage._m.keys()], ["fierro.session"]);
});

test("almacenamiento bloqueado no lanza y avisa que no está disponible", () => {
  const key = draftKey(ana, vaca);
  assert.equal(saveDraft(key, borrador, { storage: bloqueado }), false);
  assert.deepEqual(loadDraft(key, { storage: bloqueado }), { draft: null, disponible: false });
  clearDraft(key, { storage: bloqueado });
  clearAllDrafts({ storage: bloqueado });
});

test("un borrador corrupto se ignora", () => {
  const storage = memoria();
  const key = draftKey(ana, vaca);
  storage.setItem(key, "{no es json");
  assert.deepEqual(loadDraft(key, { storage }), { draft: null, disponible: true });
  assert.equal(storage.getItem(key), null);
});
