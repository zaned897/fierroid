/**
 * Routing Middleware de Vercel (#74): firma la IP real del cliente para la
 * lista de espera.
 *
 * Todo lo que pasa por Vercel llega a Cloud Run desde las IPs de salida de
 * Vercel, así que la API no puede distinguir clientes. Aquí, en el borde,
 * Vercel conoce la IP real (`x-real-ip`, que pone él y el cliente no puede
 * fijar). La mandamos con un secreto compartido; la API solo cree en
 * `x-fierro-client-ip` si el secreto coincide (ver `client_ip` en main.py).
 *
 * Sin `FIERRO_EDGE_SECRET` no se agrega nada y la API usa la IP de conexión.
 */
import { next } from "@vercel/functions";

export const config = { matcher: "/v1/waitlist" };

export function firmar(request, secreto) {
  const headers = new Headers(request.headers);
  // Lo que mande el cliente en estos encabezados no se reenvía nunca.
  headers.delete("x-fierro-edge");
  headers.delete("x-fierro-client-ip");
  const ip = request.headers.get("x-real-ip");
  if (secreto && ip) {
    headers.set("x-fierro-edge", secreto);
    headers.set("x-fierro-client-ip", ip);
  }
  return headers;
}

export default function middleware(request) {
  return next({ request: { headers: firmar(request, process.env.FIERRO_EDGE_SECRET) } });
}
