/** Blobs de borrador en IndexedDB, separados por la misma clave de usuario/org/animal. */
import { VIGENCIA_MS } from "./bitacoraDraft.js";

function database() {
  return new Promise((resolve, reject) => {
    const request = indexedDB.open("fierro-journal-media", 1);
    request.onupgradeneeded = () => request.result.createObjectStore("drafts");
    request.onsuccess = () => resolve(request.result);
    request.onerror = () => reject(request.error);
    request.onblocked = () => reject(new Error("Almacenamiento ocupado"));
  });
}

async function operation(mode, callback) {
  const db = await database();
  try {
    return await new Promise((resolve, reject) => {
      const transaction = db.transaction("drafts", mode);
      const request = callback(transaction.objectStore("drafts"));
      transaction.oncomplete = () => resolve(request?.result);
      transaction.onerror = () => reject(transaction.error);
      transaction.onabort = () => reject(transaction.error);
    });
  } finally {
    db.close();
  }
}

export async function loadMediaDraft(key) {
  const draft = await operation("readonly", (store) => store.get(key));
  if (draft && Date.now() - draft.saved_at < VIGENCIA_MS) return draft;
  if (draft) await clearMediaDraft(key);
  return null;
}

export function saveMediaDraft(key, snapshot) {
  return operation("readwrite", (store) => store.put({ ...snapshot, saved_at: Date.now() }, key));
}

export function clearMediaDraft(key) {
  return operation("readwrite", (store) => store.delete(key));
}

export function clearAllMediaDrafts() {
  return operation("readwrite", (store) => store.clear());
}
