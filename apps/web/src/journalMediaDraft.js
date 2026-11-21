/** Blobs de borrador en IndexedDB, separados por la misma clave de usuario/org/animal. */
import { VIGENCIA_MS } from "./bitacoraDraft.js";
import { LIMITS, MAX_BYTES, MIN_AUDIO_MS } from "./journalMedia.js";

/** Una URL blob o un objeto serializado no recuperan los bytes del archivo. */
export function restoreMediaFiles(files) {
  if (!Array.isArray(files)) return [];
  return files.filter((item) => item && typeof item.attachment_id === "string" && item.attachment_id
    && Object.hasOwn(LIMITS, item.kind)
    && ((item.status === "uploaded" && item.result?.attachment_id === item.attachment_id)
      || (item.file instanceof Blob && item.file.size > 0 && item.file.size <= MAX_BYTES)))
    .map((item) => {
      if (item.status === "uploaded" && item.result?.attachment_id === item.attachment_id) return item;
      const invalidAudio = item.kind === "audio" && item.duration_ms !== undefined
        && (!Number.isFinite(item.duration_ms) || item.duration_ms < MIN_AUDIO_MS);
      return { ...item, status: item.status === "rejected" || invalidAudio ? "rejected"
        : ["uploading", "error"].includes(item.status) ? "error" : "pending" };
    });
}

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
  if (draft && Date.now() - draft.saved_at < VIGENCIA_MS) {
    return { ...draft, files: restoreMediaFiles(draft.files) };
  }
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
