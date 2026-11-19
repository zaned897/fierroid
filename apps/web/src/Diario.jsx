import { useEffect, useRef, useState } from "react";
import JournalEntries from "./JournalEntries.jsx";
import JournalForm from "./JournalForm.jsx";
import { JOURNAL_CATEGORIES, journalPath, localDay } from "./journal.js";
import useJournal from "./useJournal.js";
import usePanelResource from "./usePanelResource.js";
import "./diario.css";

const dayFormat = new Intl.DateTimeFormat("es-MX", { weekday: "long", day: "numeric", month: "long", year: "numeric" });

function NoteDialog({ org, animals, session, onExpired, onClose, onSaved }) {
  const dialog = useRef(null);
  useEffect(() => {
    const node = dialog.current;
    const opener = document.activeElement;
    node.showModal();
    return () => { node.close(); opener?.focus(); };
  }, []);
  return <dialog ref={dialog} className="journal-dialog" aria-labelledby="journal-dialog-title"
    onCancel={(event) => { event.preventDefault(); onClose(); }}>
    <div className="row">
      <h2 id="journal-dialog-title">Nueva nota</h2>
      <button type="button" onClick={onClose}>Cerrar</button>
    </div>
    <JournalForm org={org} animals={animals} session={session} onExpired={onExpired} onSaved={onSaved} />
  </dialog>;
}

function DiaryFeed({ org, filters, session, onExpired, onAnimal }) {
  const path = journalPath(org, filters);
  const { entries, cursor, busy, error, load } = useJournal(path, filters.category, session, onExpired);
  const days = new Map();
  for (const entry of entries) {
    const day = localDay(entry.occurred_at);
    if (!days.has(day)) days.set(day, []);
    days.get(day).push(entry);
  }

  return <section className="journal-feed" aria-label="Notas del diario">
    <div className="row journal-feed-heading">
      <h2>Lo que pasó en el rancho</h2>
      <button type="button" disabled={busy} onClick={() => load()}>Actualizar diario</button>
    </div>
    {busy && <p role="status">Cargando notas…</p>}
    {error && <p className="error" role="alert">{error}</p>}
    {!busy && !error && entries.length === 0 && <div className="journal-empty">
      <h3>Sin notas para esta selección</h3>
      <p>Agrega una nota o cambia los filtros para consultar otros días.</p>
    </div>}
    {[...days].map(([day, items]) => <section className="journal-day" key={day} aria-label={dayFormat.format(new Date(items[0].occurred_at))}>
      <h3><time dateTime={day}>{dayFormat.format(new Date(items[0].occurred_at))}</time></h3>
      <JournalEntries entries={items} org={org} session={session} onExpired={onExpired}
        onAnimal={(tag) => onAnimal({ tag_id: tag, org })} />
    </section>)}
    {cursor && <button className="journal-more" type="button" disabled={busy} onClick={() => load(cursor)}>Ver notas anteriores</button>}
  </section>;
}

function DiaryContent({ org, initialFilters, session, onExpired, onAnimal, onAsistente }) {
  const [filters, setFilters] = useState(() => ({ from: "", to: "", tag: initialFilters?.tag || "", category: "" }));
  const [applied, setApplied] = useState(filters);
  const [open, setOpen] = useState(false);
  const [revision, setRevision] = useState(0);
  const [saved, setSaved] = useState(false);
  const { data, error, busy, refresh } = usePanelResource("/v1/animals", session, onExpired, 0);
  const animals = (data?.animals || []).filter((animal) => animal.org === org);

  function apply(event) {
    event.preventDefault();
    setApplied({ ...filters });
    setSaved(false);
  }

  return <div className="diario">
    <div className="journal-toolbar">
      <p>Las notas de tu rancho, día a día.</p>
      <button className="journal-primary" type="button" onClick={() => { setSaved(false); setOpen(true); }}>Nueva nota</button>
    </div>
    <search className="panel journal-filters" aria-label="Filtrar el diario">
      <form onSubmit={apply}>
        <label className="campo">Desde
          <input name="from" type="date" value={filters.from} max={filters.to || undefined}
            onChange={(event) => setFilters({ ...filters, from: event.target.value })} />
        </label>
        <label className="campo">Hasta
          <input name="to" type="date" value={filters.to} min={filters.from || undefined}
            onChange={(event) => setFilters({ ...filters, to: event.target.value })} />
        </label>
        <div className="campo">
          <label htmlFor="diary-filter-animal">Animal</label>
          <select id="diary-filter-animal" name="tag" value={filters.tag} onChange={(event) => setFilters({ ...filters, tag: event.target.value })}>
            <option value="">Todos los animales y el rancho</option>
            {filters.tag && !animals.some((animal) => animal.tag_id === filters.tag) && <option value={filters.tag}>{filters.tag}</option>}
            {animals.map((animal) => <option key={animal.tag_id} value={animal.tag_id}>{animal.alias || "Sin nombre"} · {animal.tag_id}</option>)}
          </select>
        </div>
        <div className="campo">
          <label htmlFor="diary-filter-category">Categoría</label>
          <select id="diary-filter-category" name="category" value={filters.category} onChange={(event) => setFilters({ ...filters, category: event.target.value })}>
            <option value="">Todas las categorías</option>
            {Object.entries(JOURNAL_CATEGORIES).map(([key, label]) => <option key={key} value={key}>{label}</option>)}
          </select>
        </div>
        <div className="journal-filter-actions">
          <button type="submit">Aplicar filtros</button>
          <button type="button" className="dashboard-text-button" onClick={() => {
            const empty = { from: "", to: "", tag: "", category: "" };
            setFilters(empty); setApplied(empty); setSaved(false);
          }}>Limpiar filtros</button>
        </div>
      </form>
    </search>
    {error && <p className="error" role="alert">No se pudieron cargar los animales. <button type="button" onClick={refresh}>Reintentar</button></p>}
    {busy && <p role="status">Cargando animales…</p>}
    <div className="journal-assistant">
      <button type="button" onClick={() => onAsistente({ org, ...applied })}>Pregúntale a tu hato</button>
    </div>
    {saved && <p className="journal-saved" role="status">Nota guardada.</p>}
    <DiaryFeed key={`${JSON.stringify(applied)}-${revision}`} org={org} filters={applied}
      session={session} onExpired={onExpired} onAnimal={onAnimal} />
    {open && <NoteDialog org={org} animals={animals} session={session} onExpired={onExpired}
      onClose={() => setOpen(false)} onSaved={() => { setOpen(false); setSaved(true); setRevision((value) => value + 1); }} />}
  </div>;
}

function SuperuserDiary(props) {
  const { session, onExpired, initialFilters } = props;
  const { data, error, busy, refresh } = usePanelResource("/v1/orgs", session, onExpired, 0);
  const [org, setOrg] = useState(initialFilters?.org || "");
  return <>
    <label className="campo journal-org">Organización del diario
      <select value={org} onChange={(event) => setOrg(event.target.value)} disabled={busy}>
        <option value="">Elige una organización</option>
        {(data?.orgs || []).map((item) => <option key={item.slug} value={item.slug}>{item.name}</option>)}
      </select>
    </label>
    {busy && <p role="status">Cargando organizaciones…</p>}
    {error && <p className="error" role="alert">No se pudieron cargar las organizaciones. <button type="button" onClick={refresh}>Reintentar</button></p>}
    {org ? <DiaryContent key={org} {...props} org={org} initialFilters={initialFilters?.org === org ? initialFilters : null} />
      : <p>Elige una organización para consultar y registrar sus notas.</p>}
  </>;
}

export default function Diario(props) {
  if (props.session.user.is_superuser) return <SuperuserDiary {...props} />;
  const org = props.session.user.org;
  if (!org) return <p className="error" role="alert">Tu cuenta necesita una organización para usar el Diario.</p>;
  return <DiaryContent {...props} org={org} />;
}
