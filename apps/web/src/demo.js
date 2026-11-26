/**
 * Rancho demo de la cuenta (016).
 *
 * Cada cuenta real puede tener un rancho demo aparte (`user.demo_org`). Con el
 * interruptor encendido, toda llamada a `/v1/` sale con `?org=<demo>`, y la
 * API la acota a ese rancho. Se hace aquí, en un solo lugar, para que ninguna
 * pantalla se quede mostrando lo real mientras el aviso dice "demostración",
 * ni al revés.
 */

/** ¿Está encendido el modo demo en esta sesión? */
export function demoActivo(session) {
  return Boolean(session?.demo && session?.user?.demo_org);
}

/**
 * Agrega `org=<demo>` a la ruta si el modo demo está encendido.
 *
 * No toca `/v1/auth/*` (la sesión es de la persona, no del rancho), ni una
 * ruta que ya diga `org=`: una pantalla que abre la ficha de un animal pasa el
 * rancho de ese animal, que ya es el demo.
 */
export function conDemo(path, session) {
  if (!demoActivo(session)) return path;
  if (!path.startsWith("/v1/") || path.startsWith("/v1/auth/")) return path;
  if (/[?&]org=/.test(path)) return path;
  const separador = path.includes("?") ? "&" : "?";
  return `${path}${separador}org=${encodeURIComponent(session.user.demo_org)}`;
}

/**
 * Valor inicial del interruptor la primera vez que la cuenta entra: encendido
 * mientras la cuenta no tenga ni un pesaje real. Así quien abre la plataforma
 * antes de conectar su báscula ve un rancho vivo, y el día que llegue el primer
 * pesaje real, lo primero que ve es lo suyo.
 */
export function demoInicial(user, pesajesReales) {
  return Boolean(user?.demo_org) && pesajesReales === 0;
}
