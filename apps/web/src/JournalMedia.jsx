import { useEffect, useId, useRef, useState } from "react";
import { apiFetch } from "./auth.js";

function Media({ entryId, item, index, org, session, onExpired }) {
  const [url, setUrl] = useState(null);
  const [error, setError] = useState(false);
  const [revision, setRevision] = useState(0);
  const refreshed = useRef(false);
  const dialog = useRef(null);
  const title = useId();
  const label = item.kind === "photo" ? `Foto ${index + 1} de la nota` : `Nota de voz ${index + 1}`;

  useEffect(() => {
    const controller = new AbortController();
    let active = true;
    let objectUrl;
    setUrl(null); setError(false);
    const timeout = setTimeout(() => controller.abort(), 30000);
    async function load() {
      try {
        const location = await apiFetch(`/v1/journal/${encodeURIComponent(entryId)}/attachments/${encodeURIComponent(item.attachment_id)}?org=${encodeURIComponent(org)}`, {
          session, signal: controller.signal,
        });
        let next;
        if (location.url.startsWith("/v1/")) {
          const blob = await apiFetch(location.url, { session, signal: controller.signal, responseType: "blob" });
          if (controller.signal.aborted) return;
          objectUrl = URL.createObjectURL(blob);
          next = objectUrl;
        } else {
          if (new URL(location.url).protocol !== "https:") throw new Error("URL inválida");
          next = location.url;
        }
        if (!controller.signal.aborted) setUrl(next);
      } catch (err) {
        if (!active) return;
        if (err.unauthorized) onExpired();
        else setError(true);
      } finally { clearTimeout(timeout); }
    }
    load();
    return () => {
      active = false;
      controller.abort(); clearTimeout(timeout);
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, [entryId, item.attachment_id, org, session, onExpired, revision]);

  function failed() {
    if (!refreshed.current) {
      refreshed.current = true;
      setRevision((value) => value + 1);
    } else setError(true);
  }

  return <li className="journal-media-item">
    {error ? <div><p>No se pudo cargar {item.kind === "photo" ? "la foto" : "el audio"}.</p>
      <button type="button" onClick={() => { refreshed.current = false; setRevision((value) => value + 1); }}>Volver a cargar {item.kind === "photo" ? "foto" : "audio"}</button></div>
      : !url ? <p className="muted">Cargando {item.kind === "photo" ? "foto" : "audio"}…</p>
      : item.kind === "photo" ? <>
        <button type="button" className="journal-thumbnail" aria-label={`Ampliar ${label.toLowerCase()}`} onClick={() => dialog.current.showModal()}>
          <img src={url} alt={label} loading="lazy" onError={failed} />
        </button>
        <dialog ref={dialog} className="journal-photo-dialog" aria-labelledby={title}>
          <div className="row"><h3 id={title}>{label}</h3><button type="button" onClick={() => dialog.current.close()}>Cerrar foto</button></div>
          <img src={url} alt={label} onError={failed} />
        </dialog>
      </> : <div className="journal-audio">
        <p>{label}{item.duration_ms ? ` · ${Math.ceil(item.duration_ms / 1000)} s` : ""}</p>
        <audio controls preload="none" src={url} aria-label={label} onError={failed} />
      </div>}
  </li>;
}

export default function JournalMedia({ entry, org, session, onExpired }) {
  return <ul className="journal-media-gallery" aria-label="Adjuntos de la nota">
    {entry.attachments.map((item, index) => <Media
      key={`${session.user.email}-${org}-${entry.entry_id}-${item.attachment_id}`}
      entryId={entry.entry_id} item={item}
      index={entry.attachments.slice(0, index).filter((other) => other.kind === item.kind).length}
      org={org} session={session} onExpired={onExpired} />)}
  </ul>;
}
