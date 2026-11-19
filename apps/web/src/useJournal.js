import { useCallback, useEffect, useRef, useState } from "react";
import { apiFetch } from "./auth.js";

/** Una página visible puede recorrer varias páginas de la API por categoría. */
export default function useJournal(path, category, session, onExpired) {
  const [entries, setEntries] = useState([]);
  const [cursor, setCursor] = useState(null);
  const [busy, setBusy] = useState(true);
  const [error, setError] = useState(null);
  const request = useRef(null);

  const load = useCallback(async (next = null) => {
    request.current?.abort();
    const controller = new AbortController();
    request.current = controller;
    const timeout = setTimeout(() => controller.abort(), 15000);
    setBusy(true);
    setError(null);
    try {
      const found = new Map();
      const visited = new Set();
      let after = next;
      do {
        visited.add(after);
        const url = `${path}${after ? `&cursor=${encodeURIComponent(after)}` : ""}`;
        const page = await apiFetch(url, { session, signal: controller.signal });
        for (const entry of page.entries) {
          if (!category || entry.category === category) found.set(entry.entry_id, entry);
        }
        after = page.next_cursor || null;
        if (after && visited.has(after)) throw new Error("La API repitió una página.");
      } while (category && after && found.size < 20);
      if (request.current !== controller) return;
      setEntries((previous) => [...new Map(
        [...(next ? previous : []), ...found.values()].map((entry) => [entry.entry_id, entry]),
      ).values()]);
      setCursor(after);
    } catch (err) {
      if (request.current !== controller) return;
      if (err.unauthorized) onExpired();
      else {
        if (err.status === 403) { setEntries([]); setCursor(null); }
        setError(err.status === 404
          ? "El Diario todavía no está disponible en esta API."
          : "No se pudieron cargar las notas. Vuelve a intentar.");
      }
    } finally {
      clearTimeout(timeout);
      if (request.current === controller) {
        request.current = null;
        setBusy(false);
      }
    }
  }, [path, category, session, onExpired]);

  useEffect(() => {
    setEntries([]);
    setCursor(null);
    load();
    return () => {
      const controller = request.current;
      request.current = null;
      controller?.abort();
    };
  }, [load]);

  return { entries, cursor, busy, error, load };
}
