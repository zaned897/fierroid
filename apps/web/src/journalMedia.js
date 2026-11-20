/** Límites compartidos con la API y cola secuencial con UUID estables. */
export const MAX_BYTES = 2 * 1024 * 1024;
export const MAX_AUDIO_SECONDS = 120;
export const LIMITS = { photo: 6, audio: 2 };
export const MIN_AUDIO_MS = 1000;
export const MEDIA_TEXT = {
  shortAudio: "La nota de voz está vacía o es demasiado corta. Graba al menos un segundo antes de detenerla.",
  rejected: "Adjunto rechazado. El servidor no acepta este archivo. Quítalo para completar la nota.",
  error: "No se confirmó este adjunto. Puedes reintentar el envío o quitarlo.",
  uploading: "Subiendo adjunto…",
  uploaded: "Adjunto guardado.",
  removeRejected: "La nota ya está guardada. Quita los adjuntos rechazados para completar el envío.",
  incomplete: "La nota ya está guardada. Puedes completar el envío o quitar los adjuntos pendientes.",
  complete: "Completar nota",
};

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

export function audioAttachment(file, durationMs, current, id) {
  if (!file.size || !Number.isFinite(durationMs) || durationMs < MIN_AUDIO_MS) {
    throw new Error(MEDIA_TEXT.shortAudio);
  }
  return { ...attachment(file, "audio", current, id), duration_ms: durationMs };
}

export function isPermanentRejection(err) {
  return !err.unauthorized && err.status >= 400 && err.status < 500
    && ![401, 408, 429].includes(err.status);
}

export async function uploadAttachments(entryId, items, request, onChange = () => {}) {
  const uploaded = [];
  let current = items;
  // Un rechazo requiere quitar el archivo; ni siquiera un submit programático lo reenvía.
  if (current.some((item) => item.status === "rejected")) throw new Error(MEDIA_TEXT.rejected);
  for (const item of current) {
    const update = async (changes) => {
      current = current.map((value) => value.attachment_id === item.attachment_id ? { ...value, ...changes } : value);
      await onChange(current);
    };
    if (item.status === "uploaded") { uploaded.push(item.result); continue; }
    await update({ status: "uploading" });
    try {
      const data = new FormData();
      data.set("attachment_id", item.attachment_id);
      data.set("kind", item.kind);
      data.set("file", item.file, item.kind === "photo" ? "foto.jpg" : "nota-de-voz");
      const result = await request(`/v1/journal/${encodeURIComponent(entryId)}/attachments`, data);
      uploaded.push(result);
      await update({ status: "uploaded", result });
    } catch (err) {
      const rejected = isPermanentRejection(err);
      await update({ status: rejected ? "rejected" : "error" });
      throw err;
    }
  }
  return uploaded;
}
