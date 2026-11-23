import { useEffect, useRef, useState } from "react";
import { apiFetch } from "./auth.js";
import {
  CATEGORIAS,
  TIPOS,
  armarMovimiento,
  cambiar,
  fechaCorta,
  formatMxn,
  nuevoBorrador,
  vistaPrevia,
} from "./dinero.js";

const GUARDAR = { gasto: "Guardar gasto", compra: "Guardar compra", venta: "Guardar venta", precio_mercado: "Guardar precio" };

function Opciones({ legend, name, opciones, valor, onCambio }) {
  return (
    <fieldset className="dinero-opciones">
      <legend>{legend}</legend>
      <div>
        {opciones.map(([clave, etiqueta]) => (
          <label key={clave}>
            <input type="radio" name={name} value={clave} checked={valor === clave} onChange={() => onCambio(clave)} />
            {etiqueta}
          </label>
        ))}
      </div>
    </fieldset>
  );
}

/**
 * Captura manual en un `dialog` nativo (#175). El UUID se genera aquí y se
 * conserva mientras el contenido no cambie: un doble clic o un reintento tras
 * un corte de red mandan el mismo movimiento y la API no lo duplica (#173).
 */
export default function DineroCaptura({ abierto, inicial, animales, org, session, onExpired, onCerrar, onGuardado }) {
  const dialogo = useRef(null);
  const [b, setB] = useState(() => nuevoBorrador(inicial));
  const [error, setError] = useState(null);
  const [enviando, setEnviando] = useState(false);

  useEffect(() => {
    const d = dialogo.current;
    if (!d) return;
    if (abierto && !d.open) {
      setB(nuevoBorrador(inicial));
      setError(null);
      d.showModal();
    }
    if (!abierto && d.open) d.close();
  }, [abierto, inicial]);

  const poner = (campo) => (valor) => setB((actual) => cambiar(actual, campo, valor));
  const alEscribir = (campo) => (e) => poner(campo)(e.target.value);

  const guardar = async (evento) => {
    evento.preventDefault();
    if (enviando) return;
    const { movimiento, error: invalido } = armarMovimiento(b);
    if (invalido) {
      setError(invalido);
      return;
    }
    setEnviando(true);
    setError(null);
    try {
      const ruta = `/v1/dinero/movimientos${org ? `?org=${encodeURIComponent(org)}` : ""}`;
      await apiFetch(ruta, {
        session,
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(movimiento),
      });
      onGuardado();
      onCerrar();
    } catch (err) {
      if (err.unauthorized) onExpired();
      else setError(err.message);
    } finally {
      setEnviando(false);
    }
  };

  const previa = vistaPrevia(b);
  const conAnimal = b.kind === "compra" || b.kind === "venta" || (b.kind === "gasto" && b.scope === "animales");

  return (
    <dialog ref={dialogo} className="dinero-dialogo" aria-labelledby="dinero-captura-titulo" onClose={onCerrar} onCancel={onCerrar}>
      <form method="dialog" onSubmit={guardar} noValidate>
        <div className="dinero-dialogo-cabeza">
          <h2 id="dinero-captura-titulo">Nuevo movimiento</h2>
          <button type="button" className="dinero-cerrar" aria-label="Cerrar" onClick={onCerrar}>×</button>
        </div>

        <Opciones legend="Tipo" name="kind" opciones={TIPOS} valor={b.kind} onCambio={poner("kind")} />

        {b.kind === "gasto" && <Opciones legend="¿En qué?" name="category" opciones={CATEGORIAS} valor={b.category} onCambio={poner("category")} />}

        <div className="dinero-campos">
          {b.kind === "precio_mercado" ? (
            <label className="campo">Precio del kilo en pie
              <input inputMode="decimal" autoComplete="off" value={b.precio} onChange={alEscribir("precio")} placeholder="52.00" />
            </label>
          ) : (
            <label className="campo">Monto en pesos
              <input inputMode="decimal" autoComplete="off" value={b.monto} onChange={alEscribir("monto")} placeholder="3,000" />
            </label>
          )}
          <label className="campo">Fecha
            <input type="date" value={b.fecha} onChange={alEscribir("fecha")} required />
          </label>
        </div>

        {b.kind === "gasto" && (
          <Opciones
            legend="¿Para quién?"
            name="scope"
            opciones={[["animales", "Una vaca"], ["corral", "Un corral"], ["hato", "Todo el hato"]]}
            valor={b.scope}
            onCambio={poner("scope")}
          />
        )}

        {conAnimal && (
          <label className="campo">Animal
            <select value={b.animal} onChange={alEscribir("animal")} required>
              <option value="">Elige un arete</option>
              {animales.map((a) => <option key={a.tag_id} value={a.tag_id}>{a.alias ? `${a.tag_id} · ${a.alias}` : a.tag_id}</option>)}
            </select>
          </label>
        )}

        {b.kind === "gasto" && b.scope === "corral" && (
          <label className="campo">Corral
            <input value={b.corral} onChange={alEscribir("corral")} placeholder="2" autoComplete="off" />
          </label>
        )}
        {b.kind === "gasto" && b.scope === "corral" && (
          <p className="muted dinero-nota">Las vacas todavía no tienen corral asignado: este gasto cuenta en el total del mes, pero no se carga a ninguna vaca hasta que lo tengan.</p>
        )}

        {(b.kind === "compra" || b.kind === "venta") && (
          <label className="campo">Peso en kilos <span className="muted">(opcional)</span>
            <input inputMode="decimal" autoComplete="off" value={b.peso} onChange={alEscribir("peso")} placeholder="310" />
          </label>
        )}

        {b.kind === "gasto" && (
          <label className="campo dinero-dias">¿Para cuántos días alcanza? <span className="muted">(opcional)</span>
            <input inputMode="numeric" autoComplete="off" value={b.dias} onChange={alEscribir("dias")} placeholder="30" />
          </label>
        )}

        {previa && (
          <div className="dinero-previa" role="status">
            <span>Así se va a cargar</span>
            <strong>{formatMxn(previa.porDia.toFixed(2))} al día</strong>
            <small>{formatMxn(b.monto.replace(/,/g, ""))} ÷ {previa.dias} días, del {fechaCorta(previa.desde)} al {fechaCorta(previa.hasta)}{{ animales: ", para esa vaca.", corral: ", para el corral.", hato: ", repartido por cabeza entre las que estén ese día." }[b.scope]}</small>
          </div>
        )}

        {error && <p className="error" role="alert">{error}</p>}

        <div className="dinero-dialogo-acciones">
          <button type="button" onClick={onCerrar}>Cancelar</button>
          <button type="submit" className="dinero-primario" disabled={enviando}>{enviando ? "Guardando…" : GUARDAR[b.kind]}</button>
        </div>
      </form>
    </dialog>
  );
}
