"""Cuentas de dinero de la etapa 1 (#174): funciones puras, sin BD ni red.

Reciben movimientos con la forma de `MovementOut` de #173 (dicts con `kind`,
`estado`, `occurred_on`, `animals`, montos en `Decimal`) y pesajes crudos de la
API. Solo cuentan los movimientos con `estado == "confirmado"`: los anulados,
sus reversos y los propuestos no suman. Los pesajes se limpian con las mismas
reglas de la ficha (`hato.puntos_tendencia` e `hato.ids_atipicos`).

Las cuentas internas usan `Fraction` para que repartir no pierda centavos; las
salidas se redondean a centavos una sola vez, al final. Ninguna cifra se
inventa: si falta el precio o faltan pesajes, la cifra es `None` y trae un
`motivo`. Cada cifra trae su `fuente` (movimientos, pesajes y precio usados).

Supuestos de esta etapa (el modelo `docs/finanzas/modelo-dinero.md` que cita el
issue no existe en la base; quedan escritos en el PR):

- Un animal está activo desde su compra (o desde `desde` en `hato`, o desde
  siempre) hasta el día anterior a su venta: el día de la venta ya no carga.
- La ganancia del día compara la engorda contra el costo promedio por día en
  la misma ventana de los dos pesajes, para que un gasto suelto no la dispare.
- El efecto mercado es lo que cambió el valor del peso anterior por el cambio
  de precio entre ese pesaje y hoy. No entra en la ganancia del día.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from datetime import date, datetime, timedelta
from decimal import ROUND_HALF_UP, Decimal
from fractions import Fraction
from typing import Any

from fierro_api.hato import ids_atipicos, puntos_tendencia

CENTAVO = Decimal("0.01")
_MICROS_DIA = 86400 * 10**6

Activos = Mapping[date, Mapping[str, str | None]]


# --- utilidades ------------------------------------------------------------


def _fecha(valor: Any) -> date:
    if isinstance(valor, datetime):
        return valor.date()
    if isinstance(valor, date):
        return valor
    return date.fromisoformat(str(valor)[:10])


def _frac(valor: Any) -> Fraction:
    # Por `str` para que 400.1 kg sea 400.1 y no su aproximación binaria.
    return Fraction(Decimal(str(valor)))


def _decimal(valor: Fraction, paso: Decimal) -> Decimal:
    return (Decimal(valor.numerator) / Decimal(valor.denominator)).quantize(
        paso, rounding=ROUND_HALF_UP
    )


def _mxn(valor: Fraction) -> Decimal:
    return _decimal(valor, CENTAVO)


def _dias(inicio: date, fin: date) -> list[date]:
    """De inicio a fin, ambos incluidos."""
    return [inicio + timedelta(days=i) for i in range((fin - inicio).days + 1)]


def _confirmados(movimientos: Iterable[Mapping[str, Any]]) -> list[Mapping[str, Any]]:
    return [m for m in movimientos if m["estado"] == "confirmado"]


def _pesaje(punto: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "event_id": punto["event_id"],
        "captured_at": punto["captured_at"],
        "weight_kg": punto["weight_kg"],
    }


def _cifra(mxn: Fraction | None, motivo: str | None = None, **fuente: Any) -> dict[str, Any]:
    return {"mxn": None if mxn is None else _mxn(mxn), "motivo": motivo, "fuente": fuente}


# --- precio ----------------------------------------------------------------


def precio_vigente(movimientos: Iterable[Mapping[str, Any]], dia: date) -> dict[str, Any] | None:
    """El precio del kilo confirmado más reciente hasta `dia`, con su fuente.

    Mismo desempate que `GET /v1/dinero/precio` de #173: fecha del evento,
    luego registro y luego UUID.
    """
    precios = [
        m
        for m in _confirmados(movimientos)
        if m["kind"] == "precio_mercado" and _fecha(m["occurred_on"]) <= dia
    ]
    if not precios:
        return None
    m = max(
        precios,
        key=lambda p: (
            _fecha(p["occurred_on"]),
            str(p.get("created_at", "")),
            str(p["movement_id"]),
        ),
    )
    return {
        "precio_kg_mxn": Decimal(str(m["precio_kg_mxn"])),
        "movement_id": str(m["movement_id"]),
        "occurred_on": _fecha(m["occurred_on"]),
    }


# --- engorda ---------------------------------------------------------------


def ganancia_diaria_reciente(puntos: Sequence[Mapping[str, Any]]) -> dict[str, Any] | None:
    """kg/día entre el último pesaje limpio y el anterior con al menos un día de diferencia.

    `puntos` son pesajes ya limpios (sin pruebas ni atípicos), del más viejo
    al más nuevo, con `_t` como los deja `hato.puntos_tendencia`. Devuelve
    `None` si no hay dos pesajes separados por al menos 24 horas.
    """
    if len(puntos) < 2:
        return None
    ultimo = puntos[-1]
    for anterior in reversed(puntos[:-1]):
        micros = (ultimo["_t"] - anterior["_t"]) // timedelta(microseconds=1)
        if micros >= _MICROS_DIA:
            dias = Fraction(micros, _MICROS_DIA)
            kg = (_frac(ultimo["weight_kg"]) - _frac(anterior["weight_kg"])) / dias
            return {"kg_dia": kg, "anterior": anterior, "ultimo": ultimo}
    return None


# --- reparto ---------------------------------------------------------------


def activos_por_dia(
    hato: Mapping[str, Mapping[str, Any]],
    movimientos: Iterable[Mapping[str, Any]],
    desde: date,
    hasta: date,
) -> dict[date, dict[str, str | None]]:
    """Qué animales están activos cada día y en qué corral.

    `hato` es arete → {"corral": etiqueta o None, "desde": fecha opcional}.
    Los aretes que aparecen en compras o ventas confirmadas se agregan aunque
    no vengan en `hato`. La compra marca el alta; la venta, la baja (ese día
    ya no carga). Dos ventas confirmadas del mismo animal son un error de
    datos y se reportan, no se adivinan.
    """
    altas: dict[str, date | None] = {
        tag: _fecha(info["desde"]) if info.get("desde") else None for tag, info in hato.items()
    }
    bajas: dict[str, date] = {}
    for m in _confirmados(movimientos):
        if m["kind"] not in ("compra", "venta"):
            continue
        (tag,) = m["animals"]
        dia = _fecha(m["occurred_on"])
        if m["kind"] == "compra":
            actual = altas.get(tag)
            altas[tag] = dia if actual is None else min(actual, dia)
        elif tag in bajas:
            raise ValueError(f"El animal {tag} tiene más de una venta confirmada")
        else:
            bajas[tag] = dia
            altas.setdefault(tag, None)
    resultado: dict[date, dict[str, str | None]] = {}
    for dia in _dias(desde, hasta):
        resultado[dia] = {
            tag: (hato.get(tag) or {}).get("corral")
            for tag, alta in altas.items()
            if (alta is None or alta <= dia) and (tag not in bajas or dia < bajas[tag])
        }
    return resultado


def repartir(gasto: Mapping[str, Any], activos: Activos) -> dict[str, Any]:
    """Costo de un gasto por animal y por día, en `Fraction` exactas.

    - Con periodo, el monto se prorratea por igual entre sus días; sin
      periodo, cae completo el día del gasto.
    - Cada día se reparte por cabeza entre los activos de ese día: los
      animales nombrados, los del corral o todo el hato, según el alcance.
      Si una vaca se vende, sus días restantes los cargan las demás.
    - Lo que un día no tiene a quién cargarse queda en `sin_asignar`, a la
      vista, en vez de perderse o inventarse dueño. Un día que no viene en
      `activos` cuenta como día sin animales.

    La suma de `por_dia` más `sin_asignar` es siempre el monto del gasto.
    """
    if gasto["kind"] != "gasto":
        raise ValueError(f"Solo se reparten gastos, no {gasto['kind']}")
    if gasto.get("period_start") is not None:
        dias = _dias(_fecha(gasto["period_start"]), _fecha(gasto["period_end"]))
    else:
        dias = [_fecha(gasto["occurred_on"])]
    por_dia_monto = _frac(gasto["amount_mxn"]) / len(dias)
    nombrados = set(gasto.get("animals") or [])
    por_dia: dict[date, dict[str, Fraction]] = {}
    sin_asignar: dict[date, Fraction] = {}
    for dia in dias:
        del_dia = activos.get(dia, {})
        if gasto["scope"] == "animales":
            cargan = sorted(tag for tag in del_dia if tag in nombrados)
        elif gasto["scope"] == "corral":
            cargan = sorted(tag for tag, corral in del_dia.items() if corral == gasto["corral"])
        else:
            cargan = sorted(del_dia)
        if cargan:
            parte = por_dia_monto / len(cargan)
            por_dia[dia] = {tag: parte for tag in cargan}
        else:
            sin_asignar[dia] = por_dia_monto
    return {
        "movement_id": str(gasto["movement_id"]),
        "por_dia": por_dia,
        "sin_asignar": sin_asignar,
    }


# --- estado del animal -----------------------------------------------------


def _limpios(pesajes: Iterable[Mapping[str, Any]], tag: str, dia: date) -> list[dict[str, Any]]:
    puntos = [
        p
        for p in puntos_tendencia(dict(x) for x in pesajes if x.get("tag_id") == tag)
        if p["_t"].date() <= dia
    ]
    atipicos = ids_atipicos(puntos)
    return [p for p in puntos if p["event_id"] not in atipicos]


def _gastos_del_animal(
    tag: str, movimientos: list[Mapping[str, Any]], activos: Activos, dia: date
) -> list[tuple[date, Fraction, str, str]]:
    """(día, monto, categoría, movement_id) de cada gasto que le toca hasta `dia`."""
    filas = []
    for m in movimientos:
        if m["kind"] != "gasto" or _fecha(m["occurred_on"]) > dia:
            continue
        for d, partes in repartir(m, activos)["por_dia"].items():
            if d <= dia and tag in partes:
                filas.append((d, partes[tag], str(m["category"]), str(m["movement_id"])))
    return filas


def estado_animal(
    tag_id: str,
    dia: date,
    pesajes: Iterable[Mapping[str, Any]],
    movimientos: Iterable[Mapping[str, Any]],
    hato: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    """Cuánto vale, cuánto lleva metido y cuánto gana al día una vaca, al cierre de `dia`.

    `pesajes` son lecturas crudas (se limpian aquí); `movimientos` son todos
    los de la organización, porque los gastos de corral y hato se reparten
    entre los activos; `hato` es arete → {"corral", "desde"}. El precio del
    kilo sale de los movimientos `precio_mercado` (uno por rancho).

    Montos en `Decimal` a centavos. Si una cifra no se puede calcular, su
    `mxn` es `None` y `motivo` dice por qué: `falta_precio`,
    `faltan_pesajes`, `vendida` o `sin_costos`.
    """
    confirmados = _confirmados(movimientos)
    validos = [m for m in confirmados if _fecha(m["occurred_on"]) <= dia]
    ventas = [m for m in validos if m["kind"] == "venta" and tag_id in m["animals"]]
    if len(ventas) > 1:
        raise ValueError(f"El animal {tag_id} tiene más de una venta confirmada")
    venta = ventas[0] if ventas else None

    gastos_dias = [
        d
        for m in validos
        if m["kind"] == "gasto"
        for d in (
            _dias(_fecha(m["period_start"]), _fecha(m["period_end"]))
            if m.get("period_start") is not None
            else [_fecha(m["occurred_on"])]
        )
    ]
    activos = (
        activos_por_dia(hato, confirmados, min(gastos_dias), max(gastos_dias))
        if gastos_dias
        else {}
    )

    # Costo acumulado: compra más su parte de los gastos, hasta `dia`.
    por_categoria: dict[str, Fraction] = {}
    fuentes: list[str] = []
    for m in validos:
        if m["kind"] == "compra" and tag_id in m["animals"]:
            por_categoria["compra"] = por_categoria.get("compra", Fraction(0)) + _frac(
                m["amount_mxn"]
            )
            fuentes.append(str(m["movement_id"]))
    gastos = _gastos_del_animal(tag_id, validos, activos, dia)
    for _, monto, categoria, movement_id in gastos:
        por_categoria[categoria] = por_categoria.get(categoria, Fraction(0)) + monto
        if movement_id not in fuentes:
            fuentes.append(movement_id)
    costo = sum(por_categoria.values(), Fraction(0))
    costo_acumulado = {
        "mxn": _mxn(costo),
        "por_categoria": {k: _mxn(v) for k, v in sorted(por_categoria.items())},
        "fuente": {"movimientos": fuentes},
    }

    precio = precio_vigente(validos, dia)
    limpios = _limpios(pesajes, tag_id, dia)
    ultimo = limpios[-1] if limpios else None
    fuente_precio = precio

    # Valor de hoy, precio mínimo para no perder y resultado.
    valor: Fraction | None = None
    resultado_frac: Fraction | None = None
    if venta is not None:
        vendida = {"venta": str(venta["movement_id"])}
        valor_hoy = _cifra(None, "vendida", **vendida)
        minimo = _cifra(None, "vendida", **vendida)
        # Realizado: lo que se cobró menos lo metido. No necesita precio ni pesajes.
        resultado_frac = _frac(venta["amount_mxn"]) - costo
        resultado = _cifra(resultado_frac, movimientos=fuentes, **vendida)
    else:
        if ultimo is None or not ultimo["weight_kg"]:
            minimo = _cifra(None, "faltan_pesajes")
        else:
            minimo = _cifra(
                costo / _frac(ultimo["weight_kg"]), pesaje=_pesaje(ultimo), movimientos=fuentes
            )
        if precio is None:
            valor_hoy = _cifra(None, "falta_precio")
        elif ultimo is None:
            valor_hoy = _cifra(None, "faltan_pesajes", precio=fuente_precio)
        else:
            valor = _frac(ultimo["weight_kg"]) * _frac(precio["precio_kg_mxn"])
            valor_hoy = _cifra(valor, pesaje=_pesaje(ultimo), precio=fuente_precio)
        if valor is None:
            resultado = _cifra(None, valor_hoy["motivo"])
        else:
            # Lo que dejaría si se vendiera hoy al precio vigente.
            resultado_frac = valor - costo
            resultado = _cifra(resultado_frac, valor_hoy=valor_hoy["fuente"], movimientos=fuentes)

    # Ganancia del día y efecto mercado, sobre la ventana de los dos últimos pesajes.
    engorda = ganancia_diaria_reciente(limpios)
    if venta is not None:
        ganancia_dia = _cifra(None, "vendida", venta=str(venta["movement_id"]))
        efecto = _cifra(None, "vendida", venta=str(venta["movement_id"]))
    elif precio is None:
        ganancia_dia = _cifra(None, "falta_precio")
        efecto = _cifra(None, "falta_precio")
    elif engorda is None:
        ganancia_dia = _cifra(None, "faltan_pesajes", precio=fuente_precio)
        efecto = _cifra(None, "faltan_pesajes", precio=fuente_precio)
    else:
        desde = engorda["anterior"]["_t"].date()
        hasta = engorda["ultimo"]["_t"].date()
        en_ventana = [g for g in gastos if desde <= g[0] < hasta]
        costo_dia = sum((g[1] for g in en_ventana), Fraction(0)) / (hasta - desde).days
        p_hoy = _frac(precio["precio_kg_mxn"])
        ganancia_dia = _cifra(
            engorda["kg_dia"] * p_hoy - costo_dia,
            pesajes=[_pesaje(engorda["anterior"]), _pesaje(engorda["ultimo"])],
            precio=fuente_precio,
            movimientos=sorted({g[3] for g in en_ventana}),
        )
        ganancia_dia["kg_dia"] = round(float(engorda["kg_dia"]), 3)
        ganancia_dia["costo_dia_mxn"] = _mxn(costo_dia)
        precio_antes = precio_vigente(validos, desde)
        if precio_antes is None:
            efecto = _cifra(None, "falta_precio", precio=fuente_precio)
        else:
            efecto = _cifra(
                _frac(engorda["anterior"]["weight_kg"])
                * (p_hoy - _frac(precio_antes["precio_kg_mxn"])),
                pesaje=_pesaje(engorda["anterior"]),
                precio_antes=precio_antes,
                precio=fuente_precio,
            )

    if resultado_frac is None:
        roi: dict[str, Any] = {"valor": None, "motivo": resultado["motivo"]}
    elif costo == 0:
        roi = {"valor": None, "motivo": "sin_costos"}
    else:
        roi = {"valor": _decimal(resultado_frac / costo, Decimal("0.0001")), "motivo": None}

    return {
        "tag_id": tag_id,
        "dia": dia,
        "estado": "vendida" if venta is not None else "activa",
        "precio": fuente_precio,
        "valor_hoy": valor_hoy,
        "costo_acumulado": costo_acumulado,
        "resultado": resultado,
        "ganancia_dia_mxn": ganancia_dia,
        "efecto_mercado_mxn": efecto,
        "precio_minimo_kg": minimo,
        "roi": roi,
    }
