import { useCallback, useEffect, useState } from "react";
import { apiFetch } from "./auth.js";
import DineroCaptura from "./DineroCaptura.jsx";
import {
  concepto,
  escalera,
  fechaCorta,
  formatMxn,
  formatPct,
  hoyLocal,
  textoMotivo,
  textoPorDia,
  textoResultado,
} from "./dinero.js";
import "./dinero.css";

function Cifra({ titulo, cifra, valor, detalle, onPrecio }) {
  return (
    <div>
      <dt>{titulo}</dt>
      {valor !== null ? <dd className="dinero-numero">{valor}</dd> : <dd><Motivo cifra={cifra} onPrecio={onPrecio} /></dd>}
      {valor !== null && detalle && <dd className="muted">{detalle}</dd>}
    </div>
  );
}

/** Estado honesto: dice qué falta y, si es el precio, ofrece capturarlo. Nunca $0. */
export function Motivo({ cifra, onPrecio }) {
  const motivo = cifra?.motivo;
  return (
    <span className="dinero-motivo">
      {textoMotivo(motivo)}
      {motivo === "falta_precio" && onPrecio && <> · <button type="button" className="dinero-enlace" onClick={onPrecio}>captúralo aquí</button></>}
    </span>
  );
}

function Anular({ movimiento, ruta, session, onExpired, onHecho }) {
  const [confirmar, setConfirmar] = useState(false);
  const [ocupado, setOcupado] = useState(false);
  const [error, setError] = useState(null);
  const anular = async () => {
    setOcupado(true);
    setError(null);
    try {
      await apiFetch(ruta(`/v1/dinero/movimientos/${movimiento.movement_id}/anular`), {
        session,
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ movement_id: crypto.randomUUID(), occurred_on: hoyLocal() }),
      });
      onHecho();
    } catch (err) {
      if (err.unauthorized) onExpired();
      else setError(err.message);
      setOcupado(false);
    }
  };
  if (!confirmar) return <button type="button" onClick={() => setConfirmar(true)}>Anular</button>;
  return (
    <span className="dinero-confirmar" role="group" aria-label="Confirmar anulación">
      <span>¿Anular?</span>
      <button type="button" onClick={anular} disabled={ocupado}>{ocupado ? "Anulando…" : "Sí, anular"}</button>
      <button type="button" onClick={() => setConfirmar(false)} disabled={ocupado}>No</button>
      {error && <span className="error" role="alert">{error}</span>}
    </span>
  );
}

function textoEfecto(efecto, precio) {
  const antes = efecto?.fuente?.precio_antes?.precio_kg_mxn;
  if (!antes) return null;
  if (Number(antes) === Number(precio)) return `El kilo no cambió entre sus dos últimos pesajes (${formatMxn(precio)})`;
  return `El kilo pasó de ${formatMxn(antes)} a ${formatMxn(precio)}; no es engorda`;
}

function fuenteTexto(estado, movimientos) {
  const partes = [];
  const pesajes = estado.ganancia_dia_mxn?.fuente?.pesajes || [];
  if (pesajes.length) partes.push(`pesajes del ${pesajes.map((p) => fechaCorta(p.captured_at)).join(" y ")}`);
  else if (estado.valor_hoy?.fuente?.pesaje) partes.push(`pesaje del ${fechaCorta(estado.valor_hoy.fuente.pesaje.captured_at)}`);
  if (estado.precio) partes.push(`precio del kilo del ${fechaCorta(estado.precio.occurred_on)}`);
  const n = estado.costo_acumulado?.fuente?.movimientos?.length ?? movimientos;
  partes.push(`${n} ${n === 1 ? "movimiento" : "movimientos"}`);
  return `De dónde sale: ${partes.join(", ")}. Los gastos del hato y de corral se reparten por cabeza entre las vacas de cada día.`;
}

/** "Escalera de dinero" de la ficha (#175): lo que lleva metido contra lo que vale. */
export default function DineroAnimal({ animal, animales, session, onExpired }) {
  const [estado, setEstado] = useState(null);
  const [movimientos, setMovimientos] = useState([]);
  const [error, setError] = useState(null);
  const [captura, setCaptura] = useState(null);

  const ruta = useCallback((camino) => `${camino}?org=${encodeURIComponent(animal.org || "")}`, [animal.org]);

  const cargar = useCallback(async () => {
    const tag = encodeURIComponent(animal.tag_id);
    try {
      const [dinero, lista] = await Promise.all([
        apiFetch(ruta(`/v1/animals/${tag}/dinero`), { session }),
        apiFetch(`${ruta("/v1/dinero/movimientos")}&animal=${tag}`, { session }),
      ]);
      setEstado(dinero);
      setMovimientos(lista.movements || []);
      setError(null);
    } catch (err) {
      if (err.unauthorized) onExpired();
      else setError(err.message);
    }
  }, [animal.tag_id, ruta, session, onExpired]);

  useEffect(() => { cargar(); }, [cargar]);

  const capturaDialogo = (
    <DineroCaptura
      abierto={captura !== null}
      inicial={captura || undefined}
      animales={animales}
      org={animal.org}
      session={session}
      onExpired={onExpired}
      onCerrar={() => setCaptura(null)}
      onGuardado={cargar}
    />
  );
  const capturar = () => setCaptura({ kind: "gasto", animal: animal.tag_id });
  const capturarPrecio = () => setCaptura({ kind: "precio_mercado" });

  if (error) {
    return <section className="panel dinero" aria-labelledby="dinero-ficha-titulo">
      <h2 id="dinero-ficha-titulo">Dinero</h2>
      <p className="error" role="alert">No se pudo cargar el dinero de este animal. {error} <button type="button" onClick={cargar}>Reintentar</button></p>
    </section>;
  }
  if (!estado) return <section className="panel dinero"><h2>Dinero</h2><p role="status">Cargando dinero…</p></section>;

  const vendida = estado.estado === "vendida";
  const compro = "compra" in (estado.costo_acumulado?.por_categoria || {});
  const resultado = textoResultado(estado.resultado, { vendida });
  const porDia = textoPorDia(estado.ganancia_dia_mxn);
  const pierdeHoy = Number(estado.ganancia_dia_mxn?.mxn) < 0;
  const esc = escalera(estado);
  const precio = estado.precio?.precio_kg_mxn;
  const efecto = estado.efecto_mercado_mxn;
  const g = estado.ganancia_dia_mxn;

  return (
    <section className="dinero" aria-labelledby="dinero-ficha-titulo">
      <div className="row dinero-cabeza">
        <h2 id="dinero-ficha-titulo">Dinero</h2>
        <button type="button" className="dinero-primario" onClick={capturar}>Capturar gasto, compra o venta</button>
      </div>

      <div className="dinero-ficha">
        <article className="panel dinero-tarjeta dinero-resultado">
          <h3>{vendida ? "Desde que la compraste hasta la venta" : compro ? "Desde que la compraste" : "Con lo capturado hasta hoy"}</h3>
          {resultado ? <p className={`dinero-grande${Number(estado.resultado.mxn) < 0 ? " pierde" : ""}`}>{resultado}</p>
            : <p className="dinero-grande dinero-sin"><Motivo cifra={estado.resultado} onPrecio={capturarPrecio} /></p>}
          {!vendida && (porDia ? <>
            <p className={`dinero-dia${pierdeHoy ? " pierde" : ""}`}>Hoy {porDia.charAt(0).toLowerCase() + porDia.slice(1)} al día</p>
            <p className="muted">Sube {Number(g.kg_dia).toLocaleString("es-MX", { maximumFractionDigits: 2 })} kg al día × {formatMxn(precio)} el kilo, menos {formatMxn(g.costo_dia_mxn)} al día de lo que le gastas.</p>
          </> : <p className="dinero-dia dinero-sin">Hoy: <Motivo cifra={g} onPrecio={capturarPrecio} /></p>)}
          {!vendida && <dl className="dinero-cifras">
            <Cifra titulo="Precio mínimo para no perder" cifra={estado.precio_minimo_kg}
              valor={estado.precio_minimo_kg?.mxn == null ? null : `${formatMxn(estado.precio_minimo_kg.mxn)} /kg`}
              detalle={precio ? `Hoy el kilo está en ${formatMxn(precio)}` : "Falta el precio del kilo para comparar"} />
            <Cifra titulo="Efecto mercado (aparte)" cifra={efecto} onPrecio={capturarPrecio}
              valor={efecto?.mxn == null ? null : formatMxn(efecto.mxn, { signo: true })}
              detalle={textoEfecto(efecto, precio)} />
            <Cifra titulo="Retorno sobre lo metido" cifra={estado.roi} onPrecio={capturarPrecio}
              valor={estado.roi?.valor == null ? null : formatPct(estado.roi.valor)} />
          </dl>}
        </article>

        <article className="panel dinero-tarjeta">
          <h3>Lo que lleva metido contra lo que vale</h3>
          {esc.filas.length === 0 ? <p className="muted">Todavía no hay compra ni gastos cargados a este animal.</p> : <>
            <ul className="dinero-escalera">
              {esc.filas.map((f, i) => <li key={f.clave}>
                <span>{i === 0 && f.clave === "compra" ? f.etiqueta : `+ ${f.etiqueta}`}</span>
                <span className="dinero-barra" aria-hidden="true"><span className={`cat-${f.clave}`} style={{ inlineSize: `${Math.max(f.ancho * 100, 1)}%` }} /></span>
                <strong>{formatMxn(f.mxn)}</strong>
              </li>)}
            </ul>
            <ul className="dinero-escalera dinero-escalera-total">
              <li><span>Lleva metido</span><span className="dinero-barra" aria-hidden="true"><span className="metido" style={{ inlineSize: `${esc.metido.ancho * 100}%` }} /></span><strong>{formatMxn(esc.metido.mxn)}</strong></li>
              <li><span>Vale hoy{esc.vale && estado.valor_hoy.fuente?.pesaje ? ` · ${Number(estado.valor_hoy.fuente.pesaje.weight_kg).toLocaleString("es-MX")} kg × ${formatMxn(precio)}` : ""}</span>
                {esc.vale ? <><span className="dinero-barra" aria-hidden="true"><span className="vale" style={{ inlineSize: `${esc.vale.ancho * 100}%` }} /></span><strong>{formatMxn(esc.vale.mxn)}</strong></>
                  : <span className="dinero-sin"><Motivo cifra={estado.valor_hoy} onPrecio={capturarPrecio} /></span>}
              </li>
            </ul>
          </>}
        </article>
      </div>

      <article className="panel dinero-tarjeta dinero-movimientos">
        <div className="row dinero-cabeza">
          <h3>Movimientos de este animal</h3>
          <p className="muted">Corregir = anular y capturar de nuevo; nada se borra.</p>
        </div>
        {movimientos.length === 0 ? <p className="muted">Sin movimientos propios. Los gastos del hato o de corral se le cargan en la escalera.</p> :
          <div className="dinero-tabla" role="region" aria-label="Movimientos de este animal" tabIndex={0}>
            <table>
              <thead><tr><th scope="col">Fecha</th><th scope="col">Concepto</th><th scope="col">De dónde sale</th><th scope="col" className="num">Monto</th><th scope="col"><span className="visually-hidden">Acciones</span></th></tr></thead>
              <tbody>{movimientos.map((m) => <tr key={m.movement_id}>
                <td>{fechaCorta(m.occurred_on)}</td>
                <td><span className="dinero-fecha-movil">{fechaCorta(m.occurred_on)} · </span>{concepto(m)}</td>
                <td>{m.source_entry_id ? "Nota del diario" : "Captura manual"}</td>
                <td className="num">{formatMxn(m.amount_mxn ?? m.precio_kg_mxn)}</td>
                <td><Anular movimiento={m} ruta={ruta} session={session} onExpired={onExpired} onHecho={cargar} /></td>
              </tr>)}</tbody>
            </table>
          </div>}
        <p className="muted dinero-fuente">{fuenteTexto(estado, movimientos.length)}</p>
      </article>
      {capturaDialogo}
    </section>
  );
}
