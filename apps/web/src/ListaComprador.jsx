import { useEffect, useRef, useState } from "react";
import { buyerCsv, buyerRows, buyerSummary } from "./buyerList.js";
import { fetchReadingPages } from "./readingPages.js";
import { capturedLabel, weightValue } from "./readings.js";
import usePanelResource from "./usePanelResource.js";
import "./funciones-panel.css";

const hoy = () => {
  const now = new Date();
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}-${String(now.getDate()).padStart(2, "0")}`;
};
const kg = (n) => n.toLocaleString("es-MX", { minimumFractionDigits: 1, maximumFractionDigits: 1 });

/** Lista para el comprador (#99): un día de pesajes, arete por arete, para descargar o imprimir. */
export default function ListaComprador({ session, onExpired }) {
  const { data: devices } = usePanelResource("/v1/devices", session, onExpired, 0);
  const [dia, setDia] = useState(hoy);
  const [estacion, setEstacion] = useState("");
  const [lista, setLista] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);
  const request = useRef(null);

  useEffect(() => () => request.current?.abort(), []);
  useEffect(() => {
    const quitar = () => document.body.classList.remove("imprimir-lista");
    window.addEventListener("afterprint", quitar);
    return () => window.removeEventListener("afterprint", quitar);
  }, []);

  const armar = async (e) => {
    e.preventDefault();
    request.current?.abort();
    const controller = new AbortController();
    request.current = controller;
    // El día es el del dispositivo: medianoche local a medianoche local.
    const desde = new Date(`${dia}T00:00`).getTime();
    const hasta = new Date(`${dia}T00:00`);
    hasta.setDate(hasta.getDate() + 1);
    setBusy(true);
    setError(null);
    try {
      const result = await fetchReadingPages({ session, signal: controller.signal, deviceId: estacion || undefined, untilMs: desde, maxPages: 25 });
      if (request.current !== controller) return;
      const rows = buyerRows(result.readings, desde, hasta.getTime());
      setLista({ rows, summary: buyerSummary(rows), truncated: result.truncated, dia, estacion });
    } catch (err) {
      if (request.current !== controller) return;
      if (err.unauthorized) onExpired();
      else setError(err.message);
    } finally {
      if (request.current === controller) setBusy(false);
    }
  };

  const descargar = () => {
    const url = URL.createObjectURL(new Blob([buyerCsv(lista.rows)], { type: "text/csv;charset=utf-8" }));
    const a = document.createElement("a");
    a.href = url;
    a.download = `fierro-pesajes-${lista.dia}${lista.estacion ? `-${lista.estacion}` : ""}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const imprimir = () => {
    document.body.classList.add("imprimir-lista");
    window.print();
  };

  return <section className="panel lista-comprador" aria-labelledby="lista-comprador-titulo">
    <h2 id="lista-comprador-titulo">Lista para el comprador</h2>
    <form className="lista-comprador-filtros" onSubmit={armar}>
      <label className="campo">Día<input type="date" value={dia} max={hoy()} onChange={(e) => setDia(e.target.value)} required /></label>
      <label className="campo">Estación<select value={estacion} onChange={(e) => setEstacion(e.target.value)}>
        <option value="">Todas</option>
        {(devices?.devices || []).map((d) => <option key={d.device_id} value={d.device_id}>{d.device_id}</option>)}
      </select></label>
      <button type="submit" disabled={busy}>{busy ? "Armando…" : "Armar lista"}</button>
    </form>
    {error && <p className="error" role="alert">{error}</p>}
    {lista && lista.rows.length === 0 && <p role="status">No hay pesajes ese día{lista.estacion ? ` en ${lista.estacion}` : ""}.</p>}
    {lista && lista.rows.length > 0 && <div className="lista-comprador-documento">
      <p className="lista-comprador-encabezado"><strong>Pesajes del {new Date(`${lista.dia}T12:00`).toLocaleDateString("es-MX", { day: "numeric", month: "long", year: "numeric" })}</strong>{lista.estacion ? ` · ${lista.estacion}` : " · todas las estaciones"}</p>
      <dl className="lista-comprador-resumen">
        <div><dt>Animales</dt><dd>{lista.summary.animales}</dd></div>
        <div><dt>Peso total</dt><dd>{kg(lista.summary.totalKg)} kg</dd></div>
        <div><dt>Promedio</dt><dd>{lista.summary.promedioKg === null ? "—" : `${kg(lista.summary.promedioKg)} kg`}</dd></div>
        <div><dt>Lecturas dudosas</dt><dd>{lista.summary.dudosas}</dd></div>
      </dl>
      {lista.summary.pesajes !== lista.summary.animales && <p className="muted">{lista.summary.pesajes} pesajes de {lista.summary.animales} animales: algunos pasaron más de una vez.</p>}
      <table className="dashboard-readings">
        <thead><tr><th scope="col">Arete</th><th scope="col">Peso</th><th scope="col">Hora</th><th scope="col">Estación</th></tr></thead>
        <tbody>{lista.rows.map((r) => <tr key={r.event_id}>
          <td><span className="dashboard-tag">{r.tag_id || "Sin identificación"}</span>{r.stable === false && <span className="dashboard-warning">Peso inestable · no suma al total</span>}</td>
          <td className="dashboard-table-weight">{weightValue(r.weight_kg)} kg</td>
          <td><time dateTime={r.captured_at}>{capturedLabel(r.captured_at)}</time></td>
          <td>{r.device_id}</td>
        </tr>)}</tbody>
      </table>
      <p className="muted lista-comprador-nota">Registro de Fierro con los pesos que envió cada estación. No es un documento oficial ni certifica la báscula.
        {lista.truncated && " La lista puede estar incompleta: el día tiene más pesajes de los que se pudieron leer."}</p>
      <div className="lista-comprador-acciones">
        <button type="button" onClick={descargar}>Descargar CSV</button>
        <button type="button" onClick={imprimir}>Imprimir o guardar PDF</button>
      </div>
    </div>}
  </section>;
}
