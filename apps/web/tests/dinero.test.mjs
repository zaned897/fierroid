import assert from "node:assert/strict";
import test from "node:test";
import {
  armarMovimiento,
  cambiar,
  categoriasDelMes,
  concepto,
  escalera,
  formatMxn,
  formatPct,
  montoValido,
  nuevoBorrador,
  ordenarPorDia,
  textoMotivo,
  textoPorDia,
  textoResultado,
  vistaPrevia,
} from "../src/dinero.js";

// Respuesta de GET /v1/animals/{tag}/dinero tal como la da la API de #174.
const API_VACA = {
  tag_id: "1043", dia: "2026-10-20", estado: "activa",
  precio: { precio_kg_mxn: "45.00", movement_id: "p", occurred_on: "2026-10-01" },
  valor_hoy: { mxn: "18495.00", motivo: null, fuente: { pesaje: { event_id: "e2", captured_at: "2026-10-20T08:00:00+00:00", weight_kg: 411 } } },
  costo_acumulado: { mxn: "11000.00", por_categoria: { alimento: "1000.00", compra: "10000.00" }, fuente: { movimientos: ["c", "g"] } },
  resultado: { mxn: "7495.00", motivo: null, fuente: {} },
  ganancia_dia_mxn: { mxn: "-0.50", motivo: null, fuente: {}, kg_dia: "1.100", costo_dia_mxn: "50.00" },
  efecto_mercado_mxn: { mxn: "0.00", motivo: null, fuente: {} },
  precio_minimo_kg: { mxn: "26.76", motivo: null, fuente: {} },
  roi: { valor: "0.6814", motivo: null, fuente: {} },
};
const SIN_PRECIO = { mxn: null, motivo: "falta_precio", fuente: {} };

test("moneda: centavos solo si los hay, separador de miles y menos tipográfico", () => {
  assert.equal(formatMxn("9000.00"), "$9,000");
  assert.equal(formatMxn("50.53"), "$50.53");
  assert.equal(formatMxn("-380"), "−$380");
  assert.equal(formatMxn("604", { signo: true }), "+$604");
  assert.equal(formatMxn("0.00", { signo: true }), "$0");
  assert.equal(formatPct("0.029"), "+2.9%");
  assert.equal(formatPct("-0.1"), "−10%");
});

test("estados vacíos: sin cifra no hay $0, hay un motivo", () => {
  assert.equal(formatMxn(null), "—");
  assert.equal(formatMxn(undefined), "—");
  assert.equal(textoResultado(SIN_PRECIO), null);
  assert.equal(textoPorDia(SIN_PRECIO), null);
  assert.equal(textoMotivo("falta_precio"), "Falta precio del kilo");
  assert.equal(textoMotivo("faltan_pesajes"), "Faltan pesajes");
});

test("ganancia y pérdida se distinguen con signo y texto, no solo color", () => {
  assert.equal(textoResultado({ mxn: "2140" }), "Te ha dejado +$2,140");
  assert.equal(textoResultado({ mxn: "-380" }), "Vas −$380");
  assert.equal(textoResultado({ mxn: "3180" }, { vendida: true }), "Te dejó +$3,180");
  assert.equal(textoPorDia({ mxn: "46" }), "Gana +$46");
  assert.equal(textoPorDia({ mxn: "-4" }), "Pierde −$4");
});

test("la escalera muestra las cifras de la API sin recalcularlas", () => {
  const e = escalera(API_VACA);
  assert.deepEqual(e.filas.map((f) => [f.etiqueta, f.mxn]), [["Compra", 10000], ["Alimento", 1000]]);
  assert.equal(e.metido.mxn, 11000);
  assert.equal(e.vale.mxn, 18495);
  assert.equal(e.vale.ancho, 1);
  assert.equal(textoResultado(API_VACA.resultado), "Te ha dejado +$7,495");
  assert.equal(textoPorDia(API_VACA.ganancia_dia_mxn), "Pierde −$0.50");
  // Sin precio no hay barra de "vale hoy", pero los costos siguen.
  const sin = escalera({ ...API_VACA, valor_hoy: SIN_PRECIO });
  assert.equal(sin.vale, null);
  assert.equal(sin.metido.mxn, 11000);
});

test("el mes del hato: partes del total y orden por $/día con los sin cifra al final", () => {
  const mes = { gastos_mxn: "14150.00", por_categoria: { sanidad: "1350.00", alimento: "9000.00", otros: "0.00" } };
  const cats = categoriasDelMes(mes);
  assert.deepEqual(cats.map((c) => c.clave), ["alimento", "sanidad"]);
  assert.equal(Math.round(cats[0].parte * 100), 64);
  const animales = [
    { tag_id: "a", ganancia_dia_mxn: { mxn: "-4.00" } },
    { tag_id: "b", ganancia_dia_mxn: SIN_PRECIO },
    { tag_id: "c", ganancia_dia_mxn: { mxn: "43.00" } },
  ];
  assert.deepEqual(ordenarPorDia(animales).map((a) => a.tag_id), ["c", "a", "b"]);
  assert.deepEqual(ordenarPorDia(animales, "asc").map((a) => a.tag_id), ["a", "c", "b"]);
});

test("doble clic sin cambios manda el mismo UUID; cambiar un campo es otro movimiento", () => {
  let b = nuevoBorrador({ hoy: "2026-11-12" });
  b = cambiar(b, "monto", "3,000");
  const primero = armarMovimiento(b).movimiento;
  const segundo = armarMovimiento(b).movimiento;
  assert.equal(primero.movement_id, segundo.movement_id);
  assert.deepEqual(primero, segundo);
  assert.equal(cambiar(b, "monto", "3,000"), b);
  assert.notEqual(cambiar(b, "monto", "3,100").movement_id, b.movement_id);
});

test("armar gasto con periodo, corral, compra con peso y precio del kilo", () => {
  let b = nuevoBorrador({ hoy: "2026-11-12" });
  for (const [campo, valor] of [["monto", "3,000"], ["scope", "corral"], ["corral", " 2 "], ["dias", "30"]]) b = cambiar(b, campo, valor);
  assert.deepEqual({ ...armarMovimiento(b).movimiento, movement_id: "x" }, {
    movement_id: "x", kind: "gasto", category: "alimento", scope: "corral", corral: "2", animals: [],
    amount_mxn: "3000", occurred_on: "2026-11-12", period_start: "2026-11-12", period_end: "2026-12-11",
  });
  assert.deepEqual(vistaPrevia(b), { porDia: 100, desde: "2026-11-12", hasta: "2026-12-11", dias: 30 });

  let c = nuevoBorrador({ kind: "compra", animal: "1043", hoy: "2026-08-02" });
  c = cambiar(cambiar(c, "monto", "18000"), "peso", "310");
  assert.deepEqual({ ...armarMovimiento(c).movimiento, movement_id: "x" }, {
    movement_id: "x", kind: "compra", scope: "animales", animals: ["1043"], amount_mxn: "18000",
    weight_kg: "310", occurred_on: "2026-08-02",
  });

  const p = cambiar(nuevoBorrador({ kind: "precio_mercado", hoy: "2026-11-14" }), "precio", "52.5");
  assert.deepEqual({ ...armarMovimiento(p).movimiento, movement_id: "x" }, {
    movement_id: "x", kind: "precio_mercado", scope: "hato", animals: [], precio_kg_mxn: "52.5", occurred_on: "2026-11-14",
  });
});

test("captura inválida se dice, no se manda", () => {
  assert.match(armarMovimiento(nuevoBorrador()).error, /monto/);
  assert.equal(montoValido("0"), null);
  assert.equal(montoValido("12.345"), null);
  assert.equal(montoValido("$1,250.50"), "1250.50");
  const vaca = cambiar(cambiar(nuevoBorrador(), "monto", "85"), "scope", "animales");
  assert.match(armarMovimiento(vaca).error, /animal/);
  assert.match(armarMovimiento(cambiar(vaca, "animal", "1043")).error ?? "", /^$/);
  const dias = cambiar(cambiar(nuevoBorrador(), "monto", "85"), "dias", "0");
  assert.match(armarMovimiento(dias).error, /días/);
});

test("concepto legible de cada movimiento", () => {
  assert.equal(concepto({ kind: "compra", weight_kg: "310.00" }), "Compra · 310 kg");
  assert.equal(concepto({ kind: "gasto", category: "alimento", scope: "corral", corral: "2", period_start: "2026-11-12", period_end: "2026-12-11" }),
    "Alimento · corral 2 · del 12 nov al 11 dic");
  assert.equal(concepto({ kind: "gasto", category: "sanidad", scope: "animales" }), "Sanidad");
});
