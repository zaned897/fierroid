import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { apiFetch } from "./auth.js";
import DineroCaptura from "./DineroCaptura.jsx";
import { Motivo } from "./DineroAnimal.jsx";
import {
  categoriasDelMes,
  formatMxn,
  ordenarPorDia,
  pierde,
  textoPorDia,
  textoResultado,
  ultimosMeses,
} from "./dinero.js";
import "./dinero.css";

const pct = (parte) => `${Math.round(parte * 100)}%`;

/** "Tu dinero" del hato (#175): en qué se va, cuánto deja cada una y las vendidas. */
export default function Dinero({ session, onExpired, onAbrir }) {
  const superusuario = Boolean(session.user?.is_superuser);
  const meses = useMemo(() => ultimosMeses(12), []);
  const [mes, setMes] = useState(meses[0].valor);
  const [animales, setAnimales] = useState([]);
  const [org, setOrg] = useState("");
  const [datos, setDatos] = useState(null);
  const [error, setError] = useState(null);
  const [orden, setOrden] = useState("desc");
  const [captura, setCaptura] = useState(null);
  const pedido = useRef(null);

  useEffect(() => {
    apiFetch("/v1/animals", { session })
      .then((body) => {
        const lista = body.animals || [];
        setAnimales(lista);
        // El superusuario no tiene rancho propio: se elige uno de los que tienen animales.
        if (superusuario) setOrg((actual) => actual || lista.find((a) => a.org)?.org || "");
      })
      .catch((err) => { if (err.unauthorized) onExpired(); });
  }, [session, superusuario, onExpired]);

  const orgs = [...new Set(animales.map((a) => a.org).filter(Boolean))].sort();
  const delRancho = superusuario ? animales.filter((a) => a.org === org) : animales;

  const cargar = useCallback(async () => {
    if (superusuario && !org) return;
    pedido.current?.abort();
    const controller = new AbortController();
    pedido.current = controller;
    setError(null);
    const params = new URLSearchParams({ mes });
    if (org) params.set("org", org);
    try {
      const body = await apiFetch(`/v1/hato/dinero?${params}`, { session, signal: controller.signal });
      if (pedido.current === controller) setDatos(body);
    } catch (err) {
      if (pedido.current !== controller) return;
      if (err.unauthorized) onExpired();
      else setError(err.name === "AbortError" ? "La consulta se canceló." : err.message);
    }
  }, [mes, org, superusuario, session, onExpired]);

  useEffect(() => {
    cargar();
    return () => { pedido.current?.abort(); pedido.current = null; };
  }, [cargar]);

  const categorias = categoriasDelMes(datos?.mes);
  const ordenadas = ordenarPorDia(datos?.animales, orden);
  const perdiendo = ordenadas.filter(pierde).length;
  const alias = Object.fromEntries(delRancho.map((a) => [a.tag_id, a.alias]));
  const nombre = (tag) => (alias[tag] ? `${tag} · ${alias[tag]}` : tag);
  const etiquetaMes = meses.find((m) => m.valor === mes)?.etiqueta || mes;

  return (
    <div className="dinero">
      <div className="dinero-controles">
        {superusuario && <label className="campo">Organización
          <select value={org} onChange={(e) => setOrg(e.target.value)}>
            {orgs.length === 0 && <option value="">Sin organizaciones con animales</option>}
            {orgs.map((o) => <option key={o} value={o}>{o}</option>)}
          </select>
        </label>}
        <label className="campo">Mes
          <select value={mes} onChange={(e) => setMes(e.target.value)}>
            {meses.map((m) => <option key={m.valor} value={m.valor}>{m.etiqueta}</option>)}
          </select>
        </label>
        <button type="button" className="dinero-primario" onClick={() => setCaptura({ kind: "gasto" })} disabled={superusuario && !org}>Capturar movimiento</button>
      </div>

      {error && <p className="error" role="alert">No se pudo cargar el dinero del hato. {error} <button type="button" onClick={cargar}>Reintentar</button></p>}
      {!datos && !error && <p role="status">Cargando dinero…</p>}

      {datos && <>
        {!datos.precio && <p className="panel dinero-aviso" role="note">
          <Motivo cifra={{ motivo: "falta_precio" }} onPrecio={() => setCaptura({ kind: "precio_mercado" })} />. Sin él no se calcula cuánto vale ni cuánto deja cada vaca; los gastos sí.
        </p>}

        <dl className="dinero-resumen">
          <div className="panel"><dt>Metiste en {etiquetaMes}</dt><dd>{formatMxn(datos.mes.gastos_mxn)}</dd><dd className="muted">Gastos de esos días</dd></div>
          <div className="panel"><dt>Compraste</dt><dd>{formatMxn(datos.mes.compras_mxn)}</dd><dd className="muted">{datos.mes.fuente.compras.length} {datos.mes.fuente.compras.length === 1 ? "animal" : "animales"}</dd></div>
          <div className="panel"><dt>Vendiste</dt><dd>{formatMxn(datos.mes.ventas_mxn)}</dd><dd className="muted">{datos.mes.fuente.ventas.length} {datos.mes.fuente.ventas.length === 1 ? "animal" : "animales"}</dd></div>
        </dl>

        <div className="dinero-ficha">
          <article className="panel dinero-tarjeta">
            <h2>¿En qué se va tu dinero?</h2>
            {categorias.length === 0 ? <p className="muted">No hay gastos capturados para {etiquetaMes}.</p> : <>
              <div className="dinero-apilada" role="img" aria-label={categorias.map((c) => `${c.etiqueta} ${pct(c.parte)}`).join(", ")}>
                {categorias.map((c) => <span key={c.clave} className={`cat-${c.clave}`} style={{ flexGrow: c.mxn }} />)}
              </div>
              <div className="dinero-tabla" role="region" aria-label="Gastos por categoría" tabIndex={0}>
                <table>
                  <thead><tr><th scope="col">Categoría</th><th scope="col" className="num">Monto</th><th scope="col" className="num">Parte</th></tr></thead>
                  <tbody>{categorias.map((c) => <tr key={c.clave}>
                    <td><span className={`dinero-punto cat-${c.clave}`} aria-hidden="true" />{c.etiqueta}</td>
                    <td className="num">{formatMxn(c.mxn)}</td>
                    <td className="num">{pct(c.parte)}</td>
                  </tr>)}</tbody>
                </table>
              </div>
              {Number(datos.mes.sin_asignar_mxn) > 0 && <p className="muted">{formatMxn(datos.mes.sin_asignar_mxn)} no tuvieron a qué vaca cargarse (corral sin animales asignados o días sin hato). Cuentan en el total, no en ninguna vaca.</p>}
            </>}
          </article>

          <article className="panel dinero-tarjeta dinero-por-dia">
            <h2>Cuánto deja cada una al día</h2>
            {ordenadas.length === 0 ? <p className="muted">No hay animales activos.</p> : <>
              <div className="dinero-tabla" role="region" aria-label="Cuánto deja cada animal al día" tabIndex={0}>
                <table>
                  <thead><tr>
                    <th scope="col">Animal</th>
                    <th scope="col" className="num" aria-sort={orden === "desc" ? "descending" : "ascending"}>
                      <button type="button" className="dinero-orden" onClick={() => setOrden(orden === "desc" ? "asc" : "desc")}>Por día {orden === "desc" ? "▾" : "▴"}</button>
                    </th>
                    <th scope="col" className="num">Si se vendiera hoy</th>
                  </tr></thead>
                  <tbody>{ordenadas.map((a) => <tr key={a.tag_id} className={pierde(a) ? "pierde" : undefined}>
                    <td><button type="button" className="dinero-enlace dinero-arete" onClick={() => onAbrir(a.tag_id)}>{a.tag_id}</button>
                      {(alias[a.tag_id] || pierde(a)) && <small className="dinero-alias">{[alias[a.tag_id], pierde(a) && <span key="r" className="dinero-revisar">revisar</span>].filter(Boolean).reduce((acc, x, i) => (i ? [...acc, " · ", x] : [x]), [])}</small>}</td>
                    <td className="num"><strong>{textoPorDia(a.ganancia_dia_mxn) ?? <Motivo cifra={a.ganancia_dia_mxn} />}</strong></td>
                    <td className="num">{a.resultado?.mxn == null ? <Motivo cifra={a.resultado} /> : formatMxn(a.resultado.mxn, { signo: true })}</td>
                  </tr>)}</tbody>
                </table>
              </div>
              {perdiendo > 0 && <p className="muted">{perdiendo === 1 ? "1 vaca no se está pagando lo que come." : `${perdiendo} vacas no se están pagando lo que comen.`}</p>}
            </>}
          </article>
        </div>

        <article className="panel dinero-tarjeta dinero-vendidas-tarjeta">
          <h2>Vendidas</h2>
          {datos.vendidos.length === 0 ? <p className="muted">Todavía no hay ventas capturadas.</p> :
            <div className="dinero-tabla" role="region" aria-label="Animales vendidos" tabIndex={0}>
              <table>
                <thead><tr><th scope="col">Animal</th><th scope="col">Vendida</th><th scope="col" className="num">Días en el rancho</th><th scope="col" className="num">Venta</th><th scope="col" className="num">Resultado</th></tr></thead>
                <tbody className="dinero-vendidas">{datos.vendidos.map((v) => <tr key={v.tag_id}>
                  <td>{nombre(v.tag_id)}</td>
                  <td>{new Date(`${v.vendida_el}T12:00:00`).toLocaleDateString("es-MX", { day: "numeric", month: "short", year: "numeric" })}</td>
                  <td className="num">{v.dias_en_rancho ?? "Sin compra"}</td>
                  <td className="num">{formatMxn(v.venta_mxn)}</td>
                  <td className={`num${Number(v.resultado.mxn) < 0 ? " pierde-texto" : ""}`}><strong>{textoResultado(v.resultado, { vendida: true })}</strong></td>
                </tr>)}</tbody>
              </table>
            </div>}
          <p className="muted dinero-fuente">Cifras al {new Date(`${datos.dia}T12:00:00`).toLocaleDateString("es-MX", { day: "numeric", month: "long" })}. Gastos por devengo y repartidos por cabeza entre las vacas de cada día.{datos.precio && ` Precio del kilo: ${formatMxn(datos.precio.precio_kg_mxn)}, capturado el ${new Date(`${datos.precio.occurred_on}T12:00:00`).toLocaleDateString("es-MX", { day: "numeric", month: "short" })}.`}</p>
        </article>
      </>}

      <DineroCaptura
        abierto={captura !== null}
        inicial={captura || undefined}
        animales={delRancho}
        org={org || undefined}
        session={session}
        onExpired={onExpired}
        onCerrar={() => setCaptura(null)}
        onGuardado={cargar}
      />
    </div>
  );
}
