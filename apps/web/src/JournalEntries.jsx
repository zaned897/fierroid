import { JOURNAL_CATEGORIES } from "./journal.js";
import { capturedLabel } from "./readings.js";
import JournalMedia from "./JournalMedia.jsx";

export default function JournalEntries({ entries, onAnimal, org, session, onExpired }) {
  return <ol className="journal-entries">
    {entries.map((entry) => <li key={entry.entry_id} id={`nota-${entry.entry_id}`}>
      <div className="journal-entry-heading">
        <strong>{JOURNAL_CATEGORIES[entry.category] || entry.category}</strong>
        <time dateTime={entry.occurred_at}>{capturedLabel(entry.occurred_at)}</time>
      </div>
      <p className="animal-journal-body">{entry.body}</p>
      {entry.attachments?.length > 0 && <JournalMedia entry={entry} org={org} session={session} onExpired={onExpired} />}
      {entry.animals?.length > 0 && <ul className="journal-entry-animals" aria-label="Animales de la nota">
        {entry.animals.map((tag) => <li key={tag}>{onAnimal
          ? <button type="button" onClick={() => onAnimal(tag)}>{tag}</button>
          : <span>{tag}</span>}</li>)}
      </ul>}
      <p className="journal-entry-author">{entry.author} · Registrado {capturedLabel(entry.created_at)}</p>
    </li>)}
  </ol>;
}
