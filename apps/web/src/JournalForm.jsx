import { useEffect, useId, useRef, useState } from "react";
import { apiFetch } from "./auth.js";
import { clearDraft, diaryDraftKey, draftKey, loadDraft, saveDraft } from "./bitacoraDraft.js";
import { JOURNAL_CATEGORIES, localDateTime } from "./journal.js";
import JournalMediaPicker from "./JournalMediaPicker.jsx";
import { uploadAttachments } from "./journalMedia.js";
import { clearMediaDraft, loadMediaDraft, saveMediaDraft } from "./journalMediaDraft.js";

export default function JournalForm({ animal, animals = [], org, session, onExpired, onSaved }) {
  const draftId = animal ? draftKey(session.user, animal) : diaryDraftKey(session.user, org);
  const [initial] = useState(() => loadDraft(draftId));
  const [unavailable, setUnavailable] = useState(!initial.disponible);
  const [body, setBody] = useState(initial.draft?.body ?? "");
  const [category, setCategory] = useState(initial.draft?.category ?? (animal ? "observacion" : "general"));
  const [occurred, setOccurred] = useState(initial.draft?.occurred ?? localDateTime);
  const [tags, setTags] = useState(initial.draft?.animals ?? []);
  const [search, setSearch] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);
  const [files, setFiles] = useState([]);
  const [ready, setReady] = useState(false);
  const [mediaUnavailable, setMediaUnavailable] = useState(false);
  const [mediaWorking, setMediaWorking] = useState(false);
  const [confirmed, setConfirmed] = useState(initial.draft?.confirmed ?? null);
  const request = useRef(null);
  const pending = useRef(initial.draft?.entry_id
    ? { fingerprint: initial.draft.fingerprint, entry_id: initial.draft.entry_id }
    : null);
  const helpId = useId();
  const term = search.trim().toLocaleLowerCase("es");
  const visible = animals.filter((item) => [item.tag_id, item.alias]
    .some((value) => (value || "").toLocaleLowerCase("es").includes(term)));

  useEffect(() => {
    let active = true;
    loadMediaDraft(draftId).then((snapshot) => {
      if (!active || !snapshot) return;
      setFiles(snapshot.files || []);
      if (snapshot.confirmed || snapshot.saved_at >= (initial.draft?.saved_at || 0)) {
        setBody(snapshot.body); setCategory(snapshot.category);
        setOccurred(snapshot.occurred); setTags(snapshot.animals || []);
        pending.current = snapshot.pending || null;
        setConfirmed(snapshot.confirmed || null);
      }
    }).catch(() => { if (active) setMediaUnavailable(true); })
      .finally(() => { if (active) setReady(true); });
    return () => { active = false; };
  }, [draftId, initial]);

  useEffect(() => {
    if (!ready) return;
    if (!body.trim() && !pending.current) { clearDraft(draftId); return; }
    if (!saveDraft(draftId, { body, category, occurred, animals: tags, ...pending.current, confirmed })) {
      setUnavailable(true);
    }
  }, [draftId, body, category, occurred, tags, confirmed, ready]);

  useEffect(() => {
    if (!ready) return;
    const write = !body.trim() && !files.length && !pending.current
      ? clearMediaDraft(draftId)
      : saveMediaDraft(draftId, { body, category, occurred, animals: tags, files, pending: pending.current, confirmed });
    write.catch(() => setMediaUnavailable(true));
  }, [draftId, body, category, occurred, tags, files, confirmed, ready]);

  useEffect(() => () => {
    const controller = request.current;
    request.current = null;
    controller?.abort();
  }, []);

  async function save(event) {
    event.preventDefault();
    if (request.current || !ready || mediaWorking || !body.trim() || !Number.isFinite(Date.parse(occurred))) return;
    const content = { body: body.trim(), category, occurred_at: new Date(occurred).toISOString() };
    if (!animal) content.animals = [...new Set(tags)].sort();
    const fingerprint = JSON.stringify(content);
    if (pending.current?.fingerprint !== fingerprint) {
      pending.current = { fingerprint, entry_id: crypto.randomUUID() };
    }
    // Persistir el UUID antes de enviar permite recuperar una confirmación perdida.
    if (!saveDraft(draftId, { body, category, occurred, animals: tags, ...pending.current, confirmed })) {
      setUnavailable(true);
    }
    const controller = new AbortController();
    request.current = controller;
    let timeout;
    setBusy(true);
    setError(null);
    const path = animal ? `/v1/animals/${encodeURIComponent(animal.tag_id)}/journal` : "/v1/journal";
    const call = async (url, options) => {
      clearTimeout(timeout);
      timeout = setTimeout(() => controller.abort(), 30000);
      return apiFetch(`${url}?org=${encodeURIComponent(org)}`, { ...options, session, signal: controller.signal });
    };
    try {
      await saveMediaDraft(draftId, { body, category, occurred, animals: tags, files, pending: pending.current, confirmed })
        .catch(() => setMediaUnavailable(true));
      const entry = confirmed || await call(path, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ ...content, entry_id: pending.current.entry_id }),
      });
      if (request.current !== controller) return;
      setConfirmed(entry);
      await saveMediaDraft(draftId, { body, category, occurred, animals: tags, files, pending: pending.current, confirmed: entry })
        .catch(() => setMediaUnavailable(true));
      const attachments = await uploadAttachments(entry.entry_id, files, (url, data) => call(url, { method: "POST", body: data }));
      if (request.current !== controller) return;
      pending.current = null;
      clearDraft(draftId);
      await clearMediaDraft(draftId).catch(() => setMediaUnavailable(true));
      setConfirmed(null);
      setFiles([]);
      setBody("");
      setOccurred(localDateTime());
      onSaved({ ...entry, attachments });
    } catch (err) {
      if (request.current !== controller) return;
      if (err.unauthorized) onExpired();
      else setError(err.status === 409
        ? "Ese envío ya corresponde a otra nota. Revisa el texto antes de volver a guardar."
        : "No se confirmó el guardado completo. Conservamos el texto y los adjuntos. Reintenta sin modificarlos.");
    } finally {
      clearTimeout(timeout);
      if (request.current === controller) {
        request.current = null;
        setBusy(false);
      }
    }
  }

  const locked = busy || !ready || !!confirmed;
  return <form className="journal-form" onSubmit={save} aria-label={animal ? "Anotar en la bitácora" : "Nueva nota"}>
    <label className="campo">{animal ? "Anotación" : "Nota"}
      <textarea name="body" rows={4} maxLength={4000} required value={body} disabled={locked}
        onChange={(event) => setBody(event.target.value)} />
    </label>
    <div className="journal-form-details">
      <label className="campo">Fecha del evento (hora local)
        <input name="occurred" type="datetime-local" value={occurred} required disabled={locked}
          onChange={(event) => setOccurred(event.target.value)} />
      </label>
      <div className="campo">
        <label htmlFor={`${helpId}-category`}>Categoría</label>
        <select id={`${helpId}-category`} name="category" value={category} disabled={locked} onChange={(event) => setCategory(event.target.value)}>
          {Object.entries(JOURNAL_CATEGORIES).map(([key, label]) => <option key={key} value={key}>{label}</option>)}
        </select>
      </div>
    </div>
    {!animal && <fieldset className="journal-animal-picker" disabled={locked}>
      <legend>Animales (opcional)</legend>
      <p id={helpId} className="muted">Sin selección, la nota es del rancho.</p>
      {tags.length > 0 && <ul className="journal-selected" aria-label="Animales seleccionados">
        {tags.map((tag) => <li key={tag}><button type="button"
          aria-label={`Quitar ${tag}`} onClick={() => setTags((current) => current.filter((value) => value !== tag))}>
          {animals.find((item) => item.tag_id === tag)?.alias || tag}<span aria-hidden="true"> ×</span>
        </button></li>)}
      </ul>}
      <label className="campo">Buscar por arete o nombre
        <input name="animal-search" type="search" value={search} aria-describedby={helpId}
          onChange={(event) => setSearch(event.target.value)} />
      </label>
      <div className="journal-animal-options">
        {visible.map((item) => <label key={item.tag_id} className="journal-animal-option">
          <input type="checkbox" name="animals" value={item.tag_id} checked={tags.includes(item.tag_id)}
            disabled={!tags.includes(item.tag_id) && tags.length >= 100}
            onChange={(event) => setTags((current) => event.target.checked
              ? [...current, item.tag_id] : current.filter((tag) => tag !== item.tag_id))} />
          <span>{item.alias || "Sin nombre"}<small>{item.tag_id}</small></span>
        </label>)}
        {visible.length === 0 && <p className="muted">{term ? "Ningún animal coincide con la búsqueda." : "Aún no hay animales registrados."}</p>}
      </div>
      {tags.length >= 100 && <p role="status">Puedes seleccionar hasta 100 animales por nota.</p>}
    </fieldset>}
    <JournalMediaPicker files={files} onChange={setFiles} disabled={locked} onWorking={setMediaWorking} />
    {!ready && <p role="status">Recuperando borrador…</p>}
    {confirmed && <p role="status">La nota ya está guardada. Falta confirmar sus adjuntos; reintenta para completar el envío.</p>}
    {unavailable && <p className="muted">Este navegador no permite guardar el texto del borrador al cerrar la ventana.</p>}
    {mediaUnavailable && <p className="muted">Este navegador no permite conservar los archivos al cerrar o recargar. Mantén esta ventana abierta hasta terminar el envío.</p>}
    {error && <p className="error" role="alert">{error}</p>}
    <button className="journal-primary" type="submit" disabled={busy || !ready || mediaWorking || !body.trim()}>
      {busy ? "Guardando…" : confirmed ? "Reintentar adjuntos" : animal ? "Guardar anotación" : "Guardar nota"}
    </button>
  </form>;
}
