import { useState } from "react";
import JournalEntries from "./JournalEntries.jsx";
import JournalForm from "./JournalForm.jsx";
import useJournal from "./useJournal.js";
import "./diario.css";

export default function BitacoraAnimal({ animal, session, onExpired, onDiario }) {
  const path = `/v1/animals/${encodeURIComponent(animal.tag_id)}/journal?org=${encodeURIComponent(animal.org)}&limit=20`;
  const { entries, cursor, busy, error, load } = useJournal(path, "", session, onExpired);
  const [saved, setSaved] = useState(false);

  return <section className="animal-journal" aria-label="Bitácora del animal">
    <div className="row">
      <h3>Bitácora</h3>
      {onDiario && <button type="button" onClick={() => onDiario({ org: animal.org, tag: animal.tag_id })}>Ver en el diario</button>}
      <button type="button" disabled={busy} onClick={() => load()}>Actualizar bitácora</button>
    </div>
    <p className="muted">Agrega una anotación para registrar o aclarar lo ocurrido. Tu borrador se conserva en este navegador.</p>
    <JournalForm animal={animal} org={animal.org} session={session} onExpired={onExpired}
      onSaved={() => { setSaved(true); load(); }} />
    {busy && <p role="status">Cargando bitácora…</p>}
    {saved && <p role="status">Anotación guardada.</p>}
    {error && <p className="error" role="alert">{error}</p>}
    {!busy && !error && entries.length === 0 && <p>Todavía no hay anotaciones.</p>}
    <JournalEntries entries={entries} />
    {cursor && <button type="button" disabled={busy} onClick={() => load(cursor)}>Ver anotaciones anteriores</button>}
  </section>;
}
