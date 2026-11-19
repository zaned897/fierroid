import { JOURNAL_CATEGORIES } from "./journal.js";
import { capturedLabel } from "./readings.js";

export default function JournalEntries({ entries, onAnimal }) {
  return <ol className="journal-entries">
    {entries.map((entry) => <li key={entry.entry_id} id={`nota-${entry.entry_id}`}>
      <div className="journal-entry-heading">
        <strong>{JOURNAL_CATEGORIES[entry.category] || entry.category}</strong>
        <time dateTime={entry.occurred_at}>{capturedLabel(entry.occurred_at)}</time>
      </div>
      <p className="animal-journal-body">{entry.body}</p>
      {entry.animals?.length > 0 && <ul className="journal-entry-animals" aria-label="Animales de la nota">
        {entry.animals.map((tag) => <li key={tag}>{onAnimal
          ? <button type="button" onClick={() => onAnimal(tag)}>{tag}</button>
          : <span>{tag}</span>}</li>)}
      </ul>}
      <p className="journal-entry-author">{entry.author} · Registrado {capturedLabel(entry.created_at)}</p>
    </li>)}
  </ol>;
}
