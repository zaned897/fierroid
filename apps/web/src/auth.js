/**
 * Sesión: API key emitida por nuestra API tras validar la identidad con Google.
 *
 * La llave vive en localStorage. Es una decisión consciente del equipo con un
 * costo conocido: un XSS puede leerla. Lo que la hace tolerable es que la
 * llave es **revocable** — `DELETE /v1/auth/keys/{id}` la corta en el
 * siguiente request, cosa que con un JWT era imposible.
 */

const STORAGE_KEY = "fierro.session";

export function loadSession() {
  try {
    const crudo = localStorage.getItem(STORAGE_KEY);
    return crudo ? JSON.parse(crudo) : null;
  } catch {
    // localStorage puede estar bloqueado (modo privado, políticas). Sin sesión
    // se muestra el login, que es el comportamiento correcto.
    return null;
  }
}

export function saveSession(session) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(session));
  } catch {
    // No poder guardar significa volver a entrar al recargar. Molesto, no roto.
  }
}

export function clearSession() {
  try {
    localStorage.removeItem(STORAGE_KEY);
  } catch {
    // Nada que hacer: si no se puede escribir, tampoco se pudo guardar.
  }
}

const API_BASE = import.meta.env.VITE_API_BASE || "";

/** fetch con la credencial puesta. Lanza si la sesión ya no sirve. */
export async function apiFetch(path, { session, ...options } = {}) {
  const headers = { ...(options.headers || {}) };
  if (session?.api_key) {
    headers.Authorization = `Bearer ${session.api_key}`;
  }

  const res = await fetch(`${API_BASE}${path}`, { ...options, headers });

  if (res.status === 401) {
    // Credencial revocada, expirada o cuenta desactivada. No hay nada que
    // reintentar: la sesión terminó.
    const error = new Error("La sesión terminó. Vuelve a entrar.");
    error.unauthorized = true;
    throw error;
  }
  if (!res.ok) {
    let detalle = `${res.status} ${path}`;
    try {
      const body = await res.json();
      if (body.detail) detalle = body.detail;
    } catch {
      // Respuesta sin JSON: se queda el detalle genérico.
    }
    throw new Error(detalle);
  }
  return res.json();
}

/** Cambia el ID token de Google por una API key nuestra. */
export async function exchangeGoogleToken(idToken) {
  const res = await fetch(`${API_BASE}/v1/auth/google`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ id_token: idToken }),
  });

  const body = await res.json().catch(() => ({}));
  if (!res.ok) {
    throw new Error(body.detail || "No se pudo iniciar sesión");
  }
  return body;
}

/** Cierra esta sesión en el servidor, no solo en el navegador. */
export async function logout(session) {
  if (session?.id) {
    try {
      await apiFetch(`/v1/auth/keys/${session.id}`, { session, method: "DELETE" });
    } catch {
      // Si el servidor no responde, la llave se borra igual del navegador.
      // Peor caso: queda viva hasta expirar, y se puede revocar desde otra sesión.
    }
  }
  clearSession();
}
