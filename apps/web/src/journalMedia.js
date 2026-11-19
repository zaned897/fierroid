/** Límites compartidos con la API y cola secuencial con UUID estables. */
export const MAX_BYTES = 2 * 1024 * 1024;
export const MAX_AUDIO_SECONDS = 120;
export const LIMITS = { photo: 6, audio: 2 };

export function audioFormat(Recorder = globalThis.MediaRecorder) {
  return ["audio/webm;codecs=opus", "audio/mp4"]
    .find((type) => Recorder?.isTypeSupported?.(type)) || null;
}

export function attachment(file, kind, current, id = crypto.randomUUID()) {
  if (current.filter((item) => item.kind === kind).length >= LIMITS[kind]) {
    throw new Error(`Puedes agregar hasta ${LIMITS[kind]} ${kind === "photo" ? "fotos" : "notas de voz"}.`);
  }
  if (!file.size || file.size > MAX_BYTES) throw new Error("Cada archivo debe pesar hasta 2 MB.");
  return { attachment_id: id, kind, file };
}

export async function uploadAttachments(entryId, items, request) {
  const uploaded = [];
  for (const item of items) {
    const data = new FormData();
    data.set("attachment_id", item.attachment_id);
    data.set("kind", item.kind);
    data.set("file", item.file, item.kind === "photo" ? "foto.jpg" : "nota-de-voz");
    uploaded.push(await request(`/v1/journal/${encodeURIComponent(entryId)}/attachments`, data));
  }
  return uploaded;
}
