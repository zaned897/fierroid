import { useCallback, useEffect, useRef, useState } from "react";
import { apiFetch } from "./auth.js";

/** Una consulta a la vez; sin actividad en segundo plano ni respuestas tras salir. */
export default function usePanelResource(path, session, onExpired, pollMs = 30000) {
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(false);
  const [updatedAt, setUpdatedAt] = useState(null);
  const request = useRef(null);

  const refresh = useCallback(async () => {
    if (request.current) return;
    const controller = new AbortController();
    request.current = controller;
    setBusy(true);
    const timeout = setTimeout(() => controller.abort(), 15000);
    try {
      const body = await apiFetch(path, { session, signal: controller.signal });
      if (request.current !== controller) return;
      setData(body);
      setError(null);
      setUpdatedAt(new Date());
    } catch (err) {
      if (request.current !== controller) return;
      if (err.unauthorized) onExpired();
      else {
        if (err.status === 403) {
          setData(null);
          setUpdatedAt(null);
        }
        setError(err.name === "AbortError" ? "La consulta tardó demasiado. Vuelve a intentar." : err.message);
      }
    } finally {
      clearTimeout(timeout);
      if (request.current === controller) {
        request.current = null;
        setBusy(false);
      }
    }
  }, [path, session, onExpired]);

  useEffect(() => {
    refresh();
    const onVisible = () => { if (!document.hidden) refresh(); };
    // El historial es una instantánea: no se reemplaza mientras se pagina.
    const timer = pollMs ? setInterval(onVisible, pollMs) : null;
    if (pollMs) {
      document.addEventListener("visibilitychange", onVisible);
      window.addEventListener("online", onVisible);
    }
    return () => {
      clearInterval(timer);
      document.removeEventListener("visibilitychange", onVisible);
      window.removeEventListener("online", onVisible);
      const controller = request.current;
      request.current = null;
      controller?.abort();
    };
  }, [refresh, pollMs]);

  return { data, error, busy, updatedAt, refresh };
}
