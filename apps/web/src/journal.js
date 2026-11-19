export const JOURNAL_CATEGORIES = {
  general: "General",
  observacion: "Observación",
  alimentacion: "Alimentación",
  manejo: "Manejo",
  salud: "Salud",
  clima: "Clima",
  insumos: "Insumos",
  equipo: "Equipo",
};

export function localDateTime(date = new Date()) {
  return new Date(date.getTime() - date.getTimezoneOffset() * 60000).toISOString().slice(0, 16);
}

export function localDay(value) {
  return localDateTime(new Date(value)).slice(0, 10);
}

export function journalPath(org, { from = "", to = "", tag = "" } = {}) {
  const query = new URLSearchParams({ org, limit: "20" });
  if (tag) query.set("tag", tag);
  if (from) query.set("desde", new Date(`${from}T00:00:00`).toISOString());
  if (to) {
    const end = new Date(`${to}T00:00:00`);
    end.setDate(end.getDate() + 1);
    query.set("hasta", end.toISOString());
  }
  return `/v1/journal?${query}`;
}

export function journalQuestion({ tag, from, to }) {
  const subject = tag ? `del animal con arete ${tag}` : "de mi rancho";
  const period = [
    from && `desde el ${from}`,
    to && `hasta el ${to}`,
  ].filter(Boolean).join(" ");
  return `¿Qué información tienes ${subject}${period ? ` ${period}` : ""}?`;
}
