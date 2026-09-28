/**
 * Reduce la foto en el teléfono antes de subirla.
 *
 * Importa aquí más que en otros productos: se sube desde el corral, con LTE
 * intermitente. Una foto de 4 MB de la cámara tarda y falla; una de ~150 KB
 * sube a la primera. El servidor igual valida y limita, pero la red no es su
 * problema, es del que está parado en la manga.
 */

const LADO_MAXIMO = 1024;
const CALIDAD = 0.85;

async function normalizarTipo(file) {
  const bytes = new Uint8Array(await file.slice(0, 12).arrayBuffer());
  const empieza = (firma, offset = 0) => firma.every((byte, i) => bytes[offset + i] === byte);
  let tipo;
  let extension;
  if (empieza([0xff, 0xd8, 0xff])) {
    tipo = "image/jpeg";
    extension = "jpg";
  } else if (empieza([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a])) {
    tipo = "image/png";
    extension = "png";
  } else if (empieza([0x52, 0x49, 0x46, 0x46]) && empieza([0x57, 0x45, 0x42, 0x50], 8)) {
    tipo = "image/webp";
    extension = "webp";
  } else {
    throw new Error("Selecciona una imagen JPEG, PNG o WebP válida.");
  }
  // El sistema puede inferir el MIME de una extensión incorrecta. Conservar
  // los bytes originales; la API sigue validando el contenido recibido.
  return new File([file], `foto.${extension}`, { type: tipo, lastModified: file.lastModified });
}

export async function reducirImagen(file) {
  file = await normalizarTipo(file);
  // Si el navegador no trae createImageBitmap, se sube tal cual: mejor una
  // foto pesada que ninguna.
  if (typeof createImageBitmap !== "function") return file;

  let bitmap;
  try {
    bitmap = await createImageBitmap(file);
  } catch {
    // Archivo que el navegador no sabe decodificar. El servidor lo rechazará
    // con un mensaje claro; aquí no hay nada que decidir.
    return file;
  }

  const escala = Math.min(1, LADO_MAXIMO / Math.max(bitmap.width, bitmap.height));
  if (escala === 1 && file.size <= 500 * 1024) {
    bitmap.close?.();
    return file;
  }

  const lienzo = document.createElement("canvas");
  lienzo.width = Math.round(bitmap.width * escala);
  lienzo.height = Math.round(bitmap.height * escala);
  lienzo.getContext("2d").drawImage(bitmap, 0, 0, lienzo.width, lienzo.height);
  bitmap.close?.();

  const blob = await new Promise((resolve) =>
    lienzo.toBlob(resolve, "image/jpeg", CALIDAD),
  );
  if (!blob) return file;

  return new File([blob], "foto.jpg", { type: "image/jpeg" });
}

/**
 * La foto va detrás de credencial, así que no se puede usar `<img src>` a secas.
 * Se descarga con la llave y se entrega como object URL.
 */
export async function fetchPhotoUrl(tagId, session, org) {
  const query = org ? `?org=${encodeURIComponent(org)}` : "";
  const res = await fetch(`/v1/animals/${encodeURIComponent(tagId)}/photo${query}`, {
    headers: { Authorization: `Bearer ${session.api_key}` },
  });
  if (!res.ok) return null;
  return URL.createObjectURL(await res.blob());
}
