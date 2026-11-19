import { useEffect, useId, useRef, useState } from "react";
import { apiFetch } from "./auth.js";
import { clearDraft, diaryDraftKey, draftKey, loadDraft, saveDraft } from "./bitacoraDraft.js";
import { JOURNAL_CATEGORIES, localDateTime } from "./journal.js";

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
  const request = useRef(null);
  const pending = useRef(initial.draft?.entry_id
    ? { fingerprint: initial.draft.fingerprint, entry_id: initial.draft.entry_id }
    : null);
  const helpId = useId();
  const term = search.trim().toLocaleLowerCase("es");
  const visible = animals.filter((item) => [item.tag_id, item.alias]
    .some((value) => (value || "").toLocaleLowerCase("es").includes(term)));

  useEffect(() => {
    if (!body.trim() && !pending.current) { clearDraft(draftId); return; }
    if (!saveDraft(draftId, { body, category, occurred, animals: tags, ...pending.current })) {
      setUnavailable(true);
    }
  }, [draftId, body, category, occurred, tags]);

  useEffect(() => () => {
    const controller = request.current;
    request.current = null;
    controller?.abort();
  }, []);

  async function save(event) {
    event.preventDefault();
    if (request.current || !body.trim() || !Number.isFinite(Date.parse(occurred))) return;
    const content = { body: body.trim(), category, occurred_at: new Date(occurred).toISOString() };
    if (!animal) content.animals = [...new Set(tags)].sort();
    const fingerprint = JSON.stringify(content);
    if (pending.current?.fingerprint !== fingerprint) {
      pending.current = { fingerprint, entry_id: crypto.randomUUID() };
    }
    // Persistir el UUID antes de enviar permite recuperar una confirmación perdida.
    if (!saveDraft(draftId, { body, category, occurred, animals: tags, ...pending.current })) {
      setUnavailable(true);
    }
    const controller = new AbortController();
    request.current = controller;
    const timeout = setTimeout(() => controller.abort(), 15000);
    setBusy(true);
    setError(null);
    const path = animal ? `/v1/animals/${encodeURIComponent(animal.tag_id)}/journal` : "/v1/journal";
    try {
      const entry = await apiFetch(`${path}?org=${encodeURIComponent(org)}`, {
        session, method: "POST", signal: controller.signal,
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ ...content, entry_id: pending.current.entry_id }),
      });
      if (request.current !== controller) return;
      pending.current = null;
      clearDraft(draftId);
      setBody("");
      setOccurred(localDateTime());
      onSaved(entry);
    } catch (err) {
      if (request.current !== controller) return;
      if (err.unauthorized) onExpired();
      else setError(err.status === 409
        ? "Ese envío ya corresponde a otra nota. Revisa el texto antes de volver a guardar."
        : "No se confirmó el guardado. Conservamos el texto y los animales. Reintenta sin modificarlos.");
    } finally {
      clearTimeout(timeout);
      if (request.current === controller) {
        request.current = null;
        setBusy(false);
      }
    }
  }

  return <form className="journal-form" onSubmit={save} aria-label={animal ? "Anotar en la bitácora" : "Nueva nota"}>
    <label className="campo">{animal ? "Anotación" : "Nota"}
      <textarea name="body" rows={4} maxLength={4000} required value={body} disabled={busy}
        onChange={(event) => setBody(event.target.value)} />
    </label>
    <div className="journal-form-details">
      <label className="campo">Fecha del evento (hora local)
        <input name="occurred" type="datetime-local" value={occurred} required disabled={busy}
          onChange={(event) => setOccurred(event.target.value)} />
      </label>
      <div className="campo">
        <label htmlFor={`${helpId}-category`}>Categoría</label>
        <select id={`${helpId}-category`} name="category" value={category} disabled={busy} onChange={(event) => setCategory(event.target.value)}>
          {Object.entries(JOURNAL_CATEGORIES).map(([key, label]) => <option key={key} value={key}>{label}</option>)}
        </select>
      </div>
    </div>
    {!animal && <fieldset className="journal-animal-picker" disabled={busy}>
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
    {unavailable && <p className="muted">Este navegador no permite guardar borradores. El texto se conserva mientras esta ventana esté abierta.</p>}
    {error && <p className="error" role="alert">{error}</p>}
    <button className="journal-primary" type="submit" disabled={busy || !body.trim()}>
      {busy ? "Guardando…" : animal ? "Guardar anotación" : "Guardar nota"}
    </button>
  </form>;
}
