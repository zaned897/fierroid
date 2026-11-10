/**
 * Borrador de bitácora en el navegador.
 *
 * Guarda el texto y, sobre todo, el `entry_id` del envío en curso: si el ACK
 * se pierde y el usuario recarga, el reintento reusa el mismo UUID y la API
 * (idempotente por `entry_id`) no duplica la nota.
 *
 * La clave incluye usuario, organización y arete, así que un borrador nunca
 * aparece en la ficha de otra cuenta, otra organización u otro animal.
 * `storage` se recibe como parámetro para probarlo sin navegador; cualquier
 * error de almacenamiento (modo privado, cuota) se trata como "no disponible".
 */

export const PREFIJO = "fierro:bitacora:";
export const VIGENCIA_MS = 7 * 24 * 60 * 60 * 1000;

function almacen(storage) {
  if (storage !== undefined) return storage;
  try {
    return globalThis.localStorage ?? null;
  } catch {
    return null;
  }
}

export function draftKey(user, animal) {
  if (!user?.email || !animal?.tag_id) return null;
  return `${PREFIJO}${encodeURIComponent(user.email)}:${encodeURIComponent(animal.org ?? "")}:${encodeURIComponent(animal.tag_id)}`;
}

/** Devuelve `{ draft, disponible }`. Un borrador vencido o corrupto se descarta. */
export function loadDraft(key, { storage, now = Date.now() } = {}) {
  const s = almacen(storage);
  if (!key || !s) return { draft: null, disponible: !!s };
  try {
    const crudo = s.getItem(key);
    if (!crudo) return { draft: null, disponible: true };
    let draft = null;
    try {
      draft = JSON.parse(crudo);
    } catch {
      // Corrupto: se descarta abajo como si hubiera vencido.
    }
    if (typeof draft?.body !== "string" || !(now - draft.saved_at < VIGENCIA_MS)) {
      s.removeItem(key);
      return { draft: null, disponible: true };
    }
    return { draft, disponible: true };
  } catch {
    return { draft: null, disponible: false };
  }
}

/** Guarda el borrador. Devuelve false si el navegador no lo permite. */
export function saveDraft(key, draft, { storage, now = Date.now() } = {}) {
  const s = almacen(storage);
  if (!key || !s) return false;
  try {
    s.setItem(key, JSON.stringify({ ...draft, saved_at: now }));
    return true;
  } catch {
    return false;
  }
}

export function clearDraft(key, { storage } = {}) {
  const s = almacen(storage);
  if (!key || !s) return;
  try {
    s.removeItem(key);
  } catch {
    // Si no se puede escribir, tampoco se pudo guardar.
  }
}

/** Al cerrar sesión no queda texto de bitácora en el navegador. */
export function clearAllDrafts({ storage } = {}) {
  const s = almacen(storage);
  if (!s) return;
  try {
    const claves = [];
    for (let i = 0; i < s.length; i += 1) {
      const k = s.key(i);
      if (k?.startsWith(PREFIJO)) claves.push(k);
    }
    claves.forEach((k) => s.removeItem(k));
  } catch {
    // Igual que arriba.
  }
}
