/**
 * Dinero de la etapa 1 (#175): formato, textos y armado de movimientos.
 *
 * La web no calcula cifras de negocio: valor, costo, ganancia y reparto
 * salen de `/v1/animals/{tag}/dinero` y `/v1/hato/dinero` (#174). Aquí solo
 * se da formato, se eligen textos y se arma el JSON de captura de #173.
 */

export const CATEGORIAS = [
  ["alimento", "Alimento"],
  ["sanidad", "Sanidad"],
  ["mano_obra", "Mano de obra"],
  ["instalaciones", "Instalaciones"],
  ["transporte", "Transporte"],
  ["otros", "Otros"],
];

const ETIQUETAS = { compra: "Compra", ...Object.fromEntries(CATEGORIAS) };

export const etiquetaCategoria = (clave) => ETIQUETAS[clave] || clave;

export const TIPOS = [
  ["gasto", "Gasto"],
  ["compra", "Compra"],
  ["venta", "Venta"],
  ["precio_mercado", "Precio del kilo"],
];

const MENOS = "−";

const numero = (valor) => (valor === null || valor === undefined || valor === "" ? null : Number(valor));

/** "$9,000" o "$50.53": centavos solo cuando los hay. Sin valor, "—", nunca $0. */
export function formatMxn(valor, { signo = false } = {}) {
  const n = numero(valor);
  if (n === null || !Number.isFinite(n)) return "—";
  const entero = Math.abs(n) % 1 === 0;
  const texto = Math.abs(n).toLocaleString("es-MX", {
    minimumFractionDigits: entero ? 0 : 2,
    maximumFractionDigits: 2,
  });
  const prefijo = n < 0 ? MENOS : signo && n > 0 ? "+" : "";
  return `${prefijo}$${texto}`;
}

export function formatPct(valor) {
  const n = numero(valor);
  if (n === null) return "—";
  const pct = (n * 100).toLocaleString("es-MX", { maximumFractionDigits: 1 });
  return `${n < 0 ? MENOS + pct.replace("-", "") : n > 0 ? `+${pct}` : pct}%`;
}

/** Ganancia y pérdida con signo y texto, no solo color. */
export function textoResultado(cifra, { vendida = false } = {}) {
  const n = numero(cifra?.mxn);
  if (n === null) return null;
  if (vendida) return n < 0 ? `Te costó ${formatMxn(n)}` : `Te dejó ${formatMxn(n, { signo: true })}`;
  return n < 0 ? `Vas ${formatMxn(n)}` : `Te ha dejado ${formatMxn(n, { signo: true })}`;
}

export function textoPorDia(cifra) {
  const n = numero(cifra?.mxn);
  if (n === null) return null;
  return n < 0 ? `Pierde ${formatMxn(n)}` : `Gana ${formatMxn(n, { signo: true })}`;
}

const MOTIVOS = {
  falta_precio: "Falta precio del kilo",
  falta_precio_anterior: "Falta el precio del kilo de antes",
  faltan_pesajes: "Faltan pesajes",
  vendida: "Ya se vendió",
  sin_costos: "Sin costos capturados",
};

/** Por qué una cifra no sale. Nunca se sustituye por $0. */
export const textoMotivo = (motivo) => MOTIVOS[motivo] || "Sin datos";

/** Escalera de la ficha: compra primero, luego cada categoría, con barras sobre el mayor. */
export function escalera(estado) {
  const partes = estado?.costo_acumulado?.por_categoria || {};
  const orden = ["compra", ...CATEGORIAS.map(([k]) => k)];
  const filas = Object.entries(partes)
    .sort(([a], [b]) => orden.indexOf(a) - orden.indexOf(b))
    .map(([clave, mxn]) => ({ clave, etiqueta: etiquetaCategoria(clave), mxn: Number(mxn) }));
  const metido = numero(estado?.costo_acumulado?.mxn) ?? 0;
  const vale = numero(estado?.valor_hoy?.mxn);
  const tope = Math.max(metido, vale ?? 0) || 1;
  return {
    filas: filas.map((f) => ({ ...f, ancho: f.mxn / tope })),
    metido: { mxn: metido, ancho: metido / tope },
    vale: vale === null ? null : { mxn: vale, ancho: vale / tope },
  };
}

/** Categorías del mes con su parte del total, de mayor a menor. */
export function categoriasDelMes(mes) {
  const total = numero(mes?.gastos_mxn) ?? 0;
  return Object.entries(mes?.por_categoria || {})
    .map(([clave, mxn]) => ({ clave, etiqueta: etiquetaCategoria(clave), mxn: Number(mxn) }))
    .filter((c) => c.mxn > 0)
    .sort((a, b) => b.mxn - a.mxn)
    .map((c) => ({ ...c, parte: total ? c.mxn / total : 0 }));
}

/** Por "$/día": las que no tienen cifra van al final, sin inventarles un cero. */
export function ordenarPorDia(animales, direccion = "desc") {
  const signo = direccion === "asc" ? 1 : -1;
  return [...(animales || [])].sort((a, b) => {
    const x = numero(a.ganancia_dia_mxn?.mxn);
    const y = numero(b.ganancia_dia_mxn?.mxn);
    if (x === null && y === null) return a.tag_id.localeCompare(b.tag_id);
    if (x === null) return 1;
    if (y === null) return -1;
    return signo * (x - y) || a.tag_id.localeCompare(b.tag_id);
  });
}

export const pierde = (animal) => (numero(animal?.ganancia_dia_mxn?.mxn) ?? 0) < 0;

// --- captura -----------------------------------------------------------------

export function hoyLocal(fecha = new Date()) {
  const y = fecha.getFullYear();
  const m = String(fecha.getMonth() + 1).padStart(2, "0");
  const d = String(fecha.getDate()).padStart(2, "0");
  return `${y}-${m}-${d}`;
}

export function sumarDias(iso, dias) {
  const [y, m, d] = iso.split("-").map(Number);
  return hoyLocal(new Date(y, m - 1, d + dias));
}

const nuevoId = () => globalThis.crypto.randomUUID();

/** Borrador nuevo. El `movement_id` vive con el contenido: reintentar lo mismo no duplica. */
export function nuevoBorrador({ kind = "gasto", animal = "", hoy = hoyLocal() } = {}) {
  return {
    movement_id: nuevoId(),
    kind,
    category: "alimento",
    scope: animal ? "animales" : "hato",
    animal,
    corral: "",
    monto: "",
    precio: "",
    peso: "",
    fecha: hoy,
    dias: "",
  };
}

/**
 * Cambiar cualquier campo es otro movimiento: lleva otro UUID. Así, tras un
 * error de red, corregir el monto no choca con el intento anterior (409), y
 * un doble clic sin cambios manda el mismo UUID y la API no duplica.
 */
export function cambiar(borrador, campo, valor) {
  if (borrador[campo] === valor) return borrador;
  return { ...borrador, [campo]: valor, movement_id: nuevoId() };
}

/** Texto del usuario ("3,000", "3000.5") a decimal con dos cifras, o null. */
export function montoValido(texto) {
  const limpio = String(texto ?? "").replace(/[\s,$]/g, "");
  if (!/^\d+(\.\d{1,2})?$/.test(limpio)) return null;
  return Number(limpio) > 0 ? limpio : null;
}

/** El JSON de `POST /v1/dinero/movimientos`, o un error legible. */
export function armarMovimiento(b) {
  const base = { movement_id: b.movement_id, kind: b.kind, occurred_on: b.fecha };
  if (!b.fecha) return { error: "Elige la fecha" };
  if (b.kind === "precio_mercado") {
    const precio = montoValido(b.precio);
    if (!precio) return { error: "Escribe el precio del kilo, mayor que cero y con hasta dos decimales" };
    return { movimiento: { ...base, scope: "hato", animals: [], precio_kg_mxn: precio } };
  }
  const monto = montoValido(b.monto);
  if (!monto) return { error: "Escribe el monto en pesos, mayor que cero y con hasta dos decimales" };
  if (b.kind === "compra" || b.kind === "venta") {
    if (!b.animal) return { error: "Elige el animal" };
    const movimiento = { ...base, scope: "animales", animals: [b.animal], amount_mxn: monto };
    if (String(b.peso).trim()) {
      const peso = montoValido(b.peso);
      if (!peso) return { error: "El peso va en kilos, mayor que cero" };
      movimiento.weight_kg = peso;
    }
    return { movimiento };
  }
  const movimiento = { ...base, kind: "gasto", category: b.category, scope: b.scope, amount_mxn: monto, animals: [] };
  if (b.scope === "animales") {
    if (!b.animal) return { error: "Elige el animal" };
    movimiento.animals = [b.animal];
  }
  if (b.scope === "corral") {
    if (!b.corral.trim()) return { error: "Escribe el corral" };
    movimiento.corral = b.corral.trim();
  }
  if (String(b.dias).trim()) {
    const dias = Number(b.dias);
    if (!Number.isInteger(dias) || dias < 1 || dias > 366) return { error: "Los días van de 1 a 366" };
    movimiento.period_start = b.fecha;
    movimiento.period_end = sumarDias(b.fecha, dias - 1);
  }
  return { movimiento };
}

const MESES = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"];

/** "12 nov" a partir de "2026-11-12". */
export function fechaCorta(iso) {
  if (!iso) return "—";
  const [, m, d] = iso.slice(0, 10).split("-").map(Number);
  return `${d} ${MESES[m - 1]}`;
}

/** Lo que el formulario dice antes de guardar: solo aritmética de lo que escribiste. */
export function vistaPrevia(b) {
  const monto = montoValido(b.monto);
  const dias = Number(b.dias);
  if (b.kind !== "gasto" || !monto || !Number.isInteger(dias) || dias < 1) return null;
  return {
    porDia: Number(monto) / dias,
    desde: b.fecha,
    hasta: sumarDias(b.fecha, dias - 1),
    dias,
  };
}

/** Los últimos `n` meses, del actual hacia atrás, como "2026-11". */
export function ultimosMeses(n = 12, hoy = new Date()) {
  return Array.from({ length: n }, (_, i) => {
    const f = new Date(hoy.getFullYear(), hoy.getMonth() - i, 1);
    return {
      valor: `${f.getFullYear()}-${String(f.getMonth() + 1).padStart(2, "0")}`,
      etiqueta: f.toLocaleDateString("es-MX", { month: "long", year: "numeric" }),
    };
  });
}

/** Concepto de un movimiento para la tabla de la ficha. */
export function concepto(m) {
  if (m.kind === "precio_mercado") return `Precio del kilo · ${formatMxn(m.precio_kg_mxn)}`;
  if (m.kind === "compra" || m.kind === "venta") {
    const peso = m.weight_kg ? ` · ${Number(m.weight_kg).toLocaleString("es-MX")} kg` : "";
    return `${m.kind === "compra" ? "Compra" : "Venta"}${peso}`;
  }
  const quien = m.scope === "corral" ? ` · corral ${m.corral}` : m.scope === "hato" ? " · todo el hato" : "";
  const periodo = m.period_start ? ` · del ${fechaCorta(m.period_start)} al ${fechaCorta(m.period_end)}` : "";
  return `${etiquetaCategoria(m.category)}${quien}${periodo}`;
}
