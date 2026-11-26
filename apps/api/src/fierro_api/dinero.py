"""Cuentas de dinero de la etapa 1 (#174): funciones puras, sin BD ni red.

Reciben movimientos con la forma de `MovementOut` de #173 (dicts con `kind`,
`estado`, `occurred_on`, `animals`, montos en `Decimal`) y pesajes crudos de la
API. Solo cuentan los movimientos con `estado == "confirmado"`: los anulados,
sus reversos y los propuestos no suman. Los pesajes se limpian con las mismas
reglas de la ficha (`hato.puntos_tendencia` e `hato.ids_atipicos`).

Las cuentas internas usan `Fraction`. Al pasar a centavos, cada gasto se cuadra
por resto mayor (`cuadrar_centavos`): lo que se reparte entre animales, más lo
que queda sin asignar, suma exactamente el monto del gasto, y el costo total
de un animal es la suma de sus categorías. Ninguna cifra se inventa: si falta
el precio o faltan pesajes, la cifra es `None` y trae un `motivo`. Cada cifra
trae su `fuente` (movimientos, pesajes y precio usados).

Supuestos de esta etapa (el modelo `docs/finanzas/modelo-dinero.md` que cita el
issue no existe en la base; quedan escritos en el PR):

- Un animal está activo desde su compra (si no hay compra, desde `desde` en
  `hato`, o desde siempre) hasta el día anterior a su venta.
- Los gastos se cargan por devengo: un gasto con periodo carga los días del
  periodo hasta `dia`, aunque se haya pagado (`occurred_on`) después.
- Un gasto sin periodo de animales nombrados se carga a esos animales aunque
  ese día ya no estén activos (el flete o la guía del día de la venta).
- Los días de los pesajes se cuentan en UTC, igual que `captured_at`.
- La ganancia del día compara la engorda contra el costo promedio por día en
  la misma ventana de los dos pesajes, para que un gasto suelto no la dispare.
- El efecto mercado es lo que cambió el valor del peso anterior por el cambio
  de precio entre ese pesaje y hoy. No entra en la ganancia del día.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from datetime import UTC, date, datetime, timedelta
from decimal import ROUND_HALF_UP, Decimal, localcontext
from fractions import Fraction
from math import floor
from typing import Any

from fierro_api.hato import ids_atipicos, puntos_tendencia

CENTAVO = Decimal("0.01")
SIN_ASIGNAR = "_sin_asignar"
_MICROS_DIA = 86400 * 10**6
_ALCANCES = ("animales", "corral", "hato")
_MINIMO = datetime.min.replace(tzinfo=UTC)

Activos = Mapping[date, Mapping[str, str | None]]


class AreteDesconocido(ValueError):
    """El arete no tiene pesajes, ficha ni movimientos en esta organización."""


# --- utilidades ------------------------------------------------------------


def _fecha(valor: Any) -> date:
    """Fecha de un movimiento: `date` o texto `AAAA-MM-DD`, nada más."""
    if isinstance(valor, datetime):
        raise ValueError(f"Se esperaba una fecha sin hora, no {valor!r}")
    if isinstance(valor, date):
        return valor
    if isinstance(valor, str):
        return date.fromisoformat(valor)
    raise ValueError(f"Fecha inválida: {valor!r}")


def _instante(valor: Any) -> datetime:
    if valor is None:
        return _MINIMO
    if isinstance(valor, str):
        valor = datetime.fromisoformat(valor.replace("Z", "+00:00"))
    if not isinstance(valor, datetime):
        raise ValueError(f"Instante inválido: {valor!r}")
    return valor.astimezone(UTC) if valor.tzinfo else valor.replace(tzinfo=UTC)


def _dia_utc(punto: Mapping[str, Any]) -> date:
    instante: datetime = punto["_t"]
    return instante.astimezone(UTC).date()


def _frac(valor: Any) -> Fraction:
    # Por `str` para que 400.1 kg sea 400.1 y no su aproximación binaria.
    return Fraction(Decimal(str(valor)))


def _decimal(valor: Fraction, paso: Decimal) -> Decimal:
    with localcontext() as ctx:
        ctx.prec = 50
        return (Decimal(valor.numerator) / Decimal(valor.denominator)).quantize(
            paso, rounding=ROUND_HALF_UP
        )


def _mxn(valor: Fraction) -> Decimal:
    return _decimal(valor, CENTAVO)


def _centavos(valor: Fraction) -> int:
    return int(_mxn(valor) * 100)


def _de_centavos(centavos: int) -> Decimal:
    # Siempre con dos decimales: "11000.00", no "11000", igual que #173.
    return (Decimal(centavos) / 100).quantize(CENTAVO)


def _dias(inicio: date, fin: date) -> list[date]:
    """De inicio a fin, ambos incluidos."""
    return [inicio + timedelta(days=i) for i in range((fin - inicio).days + 1)]


def _confirmados(movimientos: Iterable[Mapping[str, Any]]) -> list[Mapping[str, Any]]:
    return [m for m in movimientos if m["estado"] == "confirmado"]


def _un_animal(m: Mapping[str, Any]) -> str:
    animales = list(m["animals"])
    if len(animales) != 1:
        raise ValueError(f"{m['kind']} {m['movement_id']} requiere exactamente un animal")
    return str(animales[0])


def _pesaje(punto: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "event_id": punto["event_id"],
        "captured_at": punto["captured_at"],
        "weight_kg": punto["weight_kg"],
    }


def _cifra(mxn: Decimal | None, motivo: str | None = None, **fuente: Any) -> dict[str, Any]:
    return {"mxn": mxn, "motivo": motivo, "fuente": fuente}


def cuadrar_centavos(partes: Mapping[str, Fraction]) -> dict[str, int]:
    """Pasa partes exactas a centavos sin perder ni inventar uno.

    El total en centavos es la suma exacta redondeada a medio centavo hacia
    arriba. Cada parte toma su piso y los centavos que faltan van, uno por
    uno, a los restos mayores; los empates se resuelven por clave, para que
    el resultado no dependa del orden de entrada.
    """
    if any(v < 0 for v in partes.values()):
        raise ValueError("No se cuadran partes negativas")
    total = _centavos(sum(partes.values(), Fraction(0)))
    pisos = {k: floor(v * 100) for k, v in partes.items()}
    faltan = total - sum(pisos.values())
    orden = sorted(partes, key=lambda k: (-(partes[k] * 100 - pisos[k]), k))
    for k in orden[:faltan]:
        pisos[k] += 1
    return pisos


# --- precio ----------------------------------------------------------------


def precio_vigente(movimientos: Iterable[Mapping[str, Any]], dia: date) -> dict[str, Any] | None:
    """El precio del kilo confirmado más reciente hasta `dia`, con su fuente.

    Mismo desempate que `GET /v1/dinero/precio` de #173: fecha del evento,
    luego instante de registro (en UTC) y luego UUID.
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
            _instante(p.get("created_at")),
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
    no vengan en `hato`. La compra marca el alta (y manda sobre `desde`); la
    venta, la baja (ese día ya no carga). Dos compras o dos ventas del mismo
    animal, o una venta antes de su compra, son errores de datos: se
    reportan, no se adivinan.
    """
    if desde > hasta:
        raise ValueError(f"Rango invertido: {desde} > {hasta}")
    altas: dict[str, date | None] = {
        tag: _fecha(info["desde"]) if info.get("desde") else None for tag, info in hato.items()
    }
    compras: dict[str, date] = {}
    bajas: dict[str, date] = {}
    for m in _confirmados(movimientos):
        if m["kind"] not in ("compra", "venta"):
            continue
        tag = _un_animal(m)
        dia = _fecha(m["occurred_on"])
        destino = compras if m["kind"] == "compra" else bajas
        if tag in destino:
            raise ValueError(f"El animal {tag} tiene más de una {m['kind']} confirmada")
        destino[tag] = dia
        altas.setdefault(tag, None)
    for tag, dia in compras.items():
        if tag in bajas and bajas[tag] < dia:
            raise ValueError(f"El animal {tag} se vendió antes de comprarse")
        altas[tag] = dia
    resultado: dict[date, dict[str, str | None]] = {}
    for dia in _dias(desde, hasta):
        resultado[dia] = {
            tag: (hato.get(tag) or {}).get("corral")
            for tag, alta in altas.items()
            if (alta is None or alta <= dia) and (tag not in bajas or dia < bajas[tag])
        }
    return resultado


def _dias_del_gasto(gasto: Mapping[str, Any]) -> list[date]:
    inicio, fin = gasto.get("period_start"), gasto.get("period_end")
    if (inicio is None) != (fin is None):
        raise ValueError(f"Gasto {gasto['movement_id']}: el periodo requiere inicio y fin")
    if inicio is None:
        return [_fecha(gasto["occurred_on"])]
    if _fecha(fin) < _fecha(inicio):
        raise ValueError(f"Gasto {gasto['movement_id']}: el periodo termina antes de empezar")
    return _dias(_fecha(inicio), _fecha(fin))


def repartir(gasto: Mapping[str, Any], activos: Activos) -> dict[str, Any]:
    """Costo de un gasto confirmado por animal y por día, en `Fraction` exactas.

    - Con periodo, el monto se prorratea por igual entre sus días; sin
      periodo, cae completo el día del gasto.
    - Cada día se reparte por cabeza entre los activos de ese día: los
      animales nombrados, los del corral o todo el hato, según el alcance.
      Si una vaca se vende, sus días restantes los cargan las demás.
    - Un gasto sin periodo de animales nombrados va a esos animales aunque
      ya no estén activos: es un gasto de ellos (flete o guía de la venta).
    - Lo que un día no tiene a quién cargarse queda en `sin_asignar`, a la
      vista, en vez de perderse o inventarse dueño. Un día que no viene en
      `activos` cuenta como día sin animales.

    La suma de `por_dia` más `sin_asignar` es siempre el monto del gasto. Un
    gasto no confirmado o mal formado es un error, no un cero.
    """
    if gasto["kind"] != "gasto":
        raise ValueError(f"Solo se reparten gastos, no {gasto['kind']}")
    if gasto["estado"] != "confirmado":
        raise ValueError(f"Gasto {gasto['movement_id']} no confirmado: {gasto['estado']}")
    monto = _frac(gasto["amount_mxn"])
    if monto <= 0:
        raise ValueError(f"Gasto {gasto['movement_id']}: el monto debe ser positivo")
    alcance = gasto["scope"]
    if alcance not in _ALCANCES:
        raise ValueError(f"Gasto {gasto['movement_id']}: alcance desconocido {alcance!r}")
    nombrados = set(gasto.get("animals") or [])
    if (alcance == "animales") != bool(nombrados):
        raise ValueError(f"Gasto {gasto['movement_id']}: solo el alcance animales lleva aretes")
    if (alcance == "corral") != bool(gasto.get("corral")):
        raise ValueError(f"Gasto {gasto['movement_id']}: solo el alcance corral lleva corral")
    dias = _dias_del_gasto(gasto)
    por_dia_monto = monto / len(dias)
    puntual = gasto.get("period_start") is None
    por_dia: dict[date, dict[str, Fraction]] = {}
    sin_asignar: dict[date, Fraction] = {}
    for dia in dias:
        del_dia = activos.get(dia, {})
        if alcance == "animales":
            cargan = sorted(nombrados if puntual else (t for t in del_dia if t in nombrados))
        elif alcance == "corral":
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


def reparto_en_centavos(reparto: Mapping[str, Any], hasta: date | None = None) -> dict[str, int]:
    """Lo que carga cada animal de un reparto hasta `hasta` (incluido), en centavos cuadrados.

    La clave `SIN_ASIGNAR` lleva lo que no tuvo a quién cargarse. Todas las
    partes suman el monto del gasto devengado hasta ese día, al centavo.
    """
    partes: dict[str, Fraction] = {}
    for dia, del_dia in reparto["por_dia"].items():
        if hasta is None or dia <= hasta:
            for tag, monto in del_dia.items():
                partes[tag] = partes.get(tag, Fraction(0)) + monto
    for dia, monto in reparto["sin_asignar"].items():
        if hasta is None or dia <= hasta:
            partes[SIN_ASIGNAR] = partes.get(SIN_ASIGNAR, Fraction(0)) + monto
    return cuadrar_centavos(partes)


# --- estado del animal -----------------------------------------------------


def _limpios(pesajes: Iterable[Mapping[str, Any]], tag: str, dia: date) -> list[dict[str, Any]]:
    puntos = [
        p
        for p in puntos_tendencia(dict(x) for x in pesajes if x.get("tag_id") == tag)
        if _dia_utc(p) <= dia
    ]
    atipicos = ids_atipicos(puntos)
    # Un peso de 0 kg no es una medición del animal: no sirve para valuarlo.
    return [p for p in puntos if p["event_id"] not in atipicos and p["weight_kg"] > 0]


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
    entre los activos; `hato` es arete → {"corral", "desde"} y debe incluir
    a `tag_id`, o el animal debe aparecer en algún movimiento. El precio del
    kilo sale de los movimientos `precio_mercado` (uno por rancho).

    Montos en `Decimal` a centavos. Si una cifra no se puede calcular, su
    `mxn` es `None` y `motivo` dice por qué: `falta_precio`,
    `falta_precio_anterior`, `faltan_pesajes`, `vendida` o `sin_costos`.
    """
    pesajes = list(pesajes)
    confirmados = _confirmados(movimientos)
    if (
        tag_id not in hato
        and not any(tag_id in (m.get("animals") or []) for m in confirmados)
        and not any(p.get("tag_id") == tag_id for p in pesajes)
    ):
        raise AreteDesconocido(f"Arete desconocido: {tag_id}")
    return _estado(_contexto(confirmados, hato, dia), tag_id, pesajes)


def _contexto(
    confirmados: list[Mapping[str, Any]], hato: Mapping[str, Mapping[str, Any]], dia: date
) -> dict[str, Any]:
    """Lo que comparten todas las vacas al cierre de `dia`: activos y reparto de cada gasto.

    Se calcula una vez por consulta; el hato completo no lo repite por animal.
    """
    hasta_dia = [m for m in confirmados if _fecha(m["occurred_on"]) <= dia]
    # Gastos por devengo: cuentan sus días hasta `dia`, se hayan pagado o no.
    gastos = [m for m in confirmados if m["kind"] == "gasto" and min(_dias_del_gasto(m)) <= dia]
    inicio = min([dia, *(min(_dias_del_gasto(m)) for m in gastos)])
    # Todos los confirmados, también los posteriores: una compra o venta
    # futura dice cuándo un animal todavía no existía o seguía activo.
    activos = activos_por_dia(hato, confirmados, inicio, dia)
    repartos = {str(m["movement_id"]): (m, repartir(m, activos)) for m in gastos}
    return {
        "dia": dia,
        "hasta_dia": hasta_dia,
        "activos": activos,
        "repartos": repartos,
        "centavos": {k: reparto_en_centavos(r, dia) for k, (_, r) in repartos.items()},
    }


def _estado(
    ctx: Mapping[str, Any], tag_id: str, pesajes: list[Mapping[str, Any]]
) -> dict[str, Any]:
    dia: date = ctx["dia"]
    hasta_dia: list[Mapping[str, Any]] = ctx["hasta_dia"]
    repartos: dict[str, tuple[Mapping[str, Any], dict[str, Any]]] = ctx["repartos"]
    ventas = [m for m in hasta_dia if m["kind"] == "venta" and _un_animal(m) == tag_id]
    venta = ventas[0] if ventas else None
    vendida = {"venta": str(venta["movement_id"])} if venta is not None else {}

    # Costo acumulado en centavos cuadrados: compra más su parte de cada gasto.
    por_categoria: dict[str, int] = {}
    fuentes: list[str] = []
    for m in hasta_dia:
        if m["kind"] == "compra" and _un_animal(m) == tag_id:
            por_categoria["compra"] = por_categoria.get("compra", 0) + _centavos(
                _frac(m["amount_mxn"])
            )
            fuentes.append(str(m["movement_id"]))
    for movement_id, (m, _) in repartos.items():
        centavos = ctx["centavos"][movement_id].get(tag_id, 0)
        if centavos:
            categoria = str(m["category"])
            por_categoria[categoria] = por_categoria.get(categoria, 0) + centavos
            fuentes.append(movement_id)
    costo = sum(por_categoria.values())
    costo_acumulado = {
        "mxn": _de_centavos(costo),
        "por_categoria": {k: _de_centavos(v) for k, v in sorted(por_categoria.items())},
        "fuente": {"movimientos": fuentes},
    }

    precio = precio_vigente(hasta_dia, dia)
    limpios = _limpios(pesajes, tag_id, dia)
    ultimo = limpios[-1] if limpios else None

    # Valor de hoy, precio mínimo para no perder y resultado.
    resultado_c: int | None = None
    if venta is not None:
        valor_hoy = _cifra(None, "vendida", **vendida)
        minimo = _cifra(None, "vendida", **vendida)
        # Realizado: lo que se cobró menos lo metido. No necesita precio ni pesajes.
        resultado_c = _centavos(_frac(venta["amount_mxn"])) - costo
        resultado = _cifra(_de_centavos(resultado_c), movimientos=fuentes, **vendida)
    else:
        if ultimo is None:
            minimo = _cifra(None, "faltan_pesajes")
        else:
            minimo = _cifra(
                _mxn(Fraction(costo, 100) / _frac(ultimo["weight_kg"])),
                pesaje=_pesaje(ultimo),
                movimientos=fuentes,
            )
        if precio is None:
            valor_hoy = _cifra(None, "falta_precio")
            resultado = _cifra(None, "falta_precio")
        elif ultimo is None:
            valor_hoy = _cifra(None, "faltan_pesajes", precio=precio)
            resultado = _cifra(None, "faltan_pesajes", precio=precio)
        else:
            valor_c = _centavos(_frac(ultimo["weight_kg"]) * _frac(precio["precio_kg_mxn"]))
            valor_hoy = _cifra(_de_centavos(valor_c), pesaje=_pesaje(ultimo), precio=precio)
            # Lo que dejaría si se vendiera hoy al precio vigente.
            resultado_c = valor_c - costo
            resultado = _cifra(
                _de_centavos(resultado_c), valor_hoy=valor_hoy["fuente"], movimientos=fuentes
            )

    # Ganancia del día y efecto mercado, sobre la ventana de los dos últimos pesajes.
    engorda = ganancia_diaria_reciente(limpios)
    if venta is not None:
        ganancia_dia = _cifra(None, "vendida", **vendida)
        efecto = _cifra(None, "vendida", **vendida)
    elif precio is None:
        ganancia_dia = _cifra(None, "falta_precio")
        efecto = _cifra(None, "falta_precio")
    elif engorda is None:
        ganancia_dia = _cifra(None, "faltan_pesajes", precio=precio)
        efecto = _cifra(None, "faltan_pesajes", precio=precio)
    else:
        # Ventana [día del anterior, día del último) en UTC. Con 24 h o más
        # entre pesajes, los días UTC siempre son distintos.
        desde = _dia_utc(engorda["anterior"])
        hasta = _dia_utc(engorda["ultimo"])
        en_ventana: dict[str, Fraction] = {}
        for movement_id, (_, reparto) in repartos.items():
            for d, partes in reparto["por_dia"].items():
                if desde <= d < hasta and tag_id in partes:
                    en_ventana[movement_id] = (
                        en_ventana.get(movement_id, Fraction(0)) + partes[tag_id]
                    )
        costo_dia = sum(en_ventana.values(), Fraction(0)) / (hasta - desde).days
        p_hoy = _frac(precio["precio_kg_mxn"])
        ganancia_dia = _cifra(
            _mxn(engorda["kg_dia"] * p_hoy - costo_dia),
            pesajes=[_pesaje(engorda["anterior"]), _pesaje(engorda["ultimo"])],
            precio=precio,
            movimientos=sorted(en_ventana),
        )
        ganancia_dia["kg_dia"] = _decimal(engorda["kg_dia"], Decimal("0.001"))
        ganancia_dia["costo_dia_mxn"] = _mxn(costo_dia)
        precio_antes = precio_vigente(hasta_dia, desde)
        if precio_antes is None:
            efecto = _cifra(None, "falta_precio_anterior", precio=precio)
        else:
            efecto = _cifra(
                _mxn(
                    _frac(engorda["anterior"]["weight_kg"])
                    * (p_hoy - _frac(precio_antes["precio_kg_mxn"]))
                ),
                pesaje=_pesaje(engorda["anterior"]),
                precio_antes=precio_antes,
                precio=precio,
            )

    roi_fuente = {"resultado": resultado["fuente"], "costo_acumulado": costo_acumulado["fuente"]}
    if resultado_c is None:
        roi = {"valor": None, "motivo": resultado["motivo"], "fuente": roi_fuente}
    elif costo == 0:
        roi = {"valor": None, "motivo": "sin_costos", "fuente": roi_fuente}
    else:
        roi = {
            "valor": _decimal(Fraction(resultado_c, costo), Decimal("0.0001")),
            "motivo": None,
            "fuente": roi_fuente,
        }

    return {
        "tag_id": tag_id,
        "dia": dia,
        "estado": "vendida" if venta is not None else "activa",
        "precio": precio,
        "valor_hoy": valor_hoy,
        "costo_acumulado": costo_acumulado,
        "resultado": resultado,
        "ganancia_dia_mxn": ganancia_dia,
        "efecto_mercado_mxn": efecto,
        "precio_minimo_kg": minimo,
        "roi": roi,
    }


# --- hato completo ---------------------------------------------------------


def dinero_del_hato(
    desde: date,
    dia: date,
    pesajes: Iterable[Mapping[str, Any]],
    movimientos: Iterable[Mapping[str, Any]],
    hato: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    """El dinero de todo el rancho: en qué se fue entre `desde` y `dia`, y cada vaca a `dia`.

    - `mes`: lo devengado entre `desde` y `dia` (ambos incluidos), por
      categoría de gasto, más compras y ventas con fecha en ese rango. Cada
      categoría incluye lo que no tuvo a quién cargarse; `sin_asignar_mxn`
      dice cuánto fue, a la vista.
    - `animales`: el estado de cada vaca activa al cierre de `dia`, con las
      mismas reglas que la ficha (`estado_animal`).
    - `vendidos`: cada venta confirmada hasta `dia`, con su resultado
      realizado y los días entre la compra y la venta (`None` sin compra).
    """
    if desde > dia:
        raise ValueError(f"Rango invertido: {desde} > {dia}")
    confirmados = _confirmados(movimientos)
    ctx = _contexto(confirmados, hato, dia)
    por_tag: dict[str, list[Mapping[str, Any]]] = {}
    for p in pesajes:
        if p.get("tag_id"):
            por_tag.setdefault(str(p["tag_id"]), []).append(p)

    por_categoria: dict[str, int] = {}
    sin_asignar = 0
    fuentes: list[str] = []
    antes = desde - timedelta(days=1)
    for movement_id, (m, reparto) in ctx["repartos"].items():
        hasta_dia = ctx["centavos"][movement_id]
        previo = reparto_en_centavos(reparto, antes)
        centavos = sum(hasta_dia.values()) - sum(previo.values())
        if centavos:
            categoria = str(m["category"])
            por_categoria[categoria] = por_categoria.get(categoria, 0) + centavos
            sin_asignar += hasta_dia.get(SIN_ASIGNAR, 0) - previo.get(SIN_ASIGNAR, 0)
            fuentes.append(movement_id)
    en_rango = [m for m in ctx["hasta_dia"] if desde <= _fecha(m["occurred_on"])]
    compras = [m for m in en_rango if m["kind"] == "compra"]
    ventas_mes = [m for m in en_rango if m["kind"] == "venta"]

    vendidos_tags = {_un_animal(m) for m in ctx["hasta_dia"] if m["kind"] == "venta"}
    compras_por_tag = {_un_animal(m): m for m in confirmados if m["kind"] == "compra"}
    animales = [
        _estado(ctx, tag, por_tag.get(tag, []))
        for tag in sorted(ctx["activos"][dia])
        if tag not in vendidos_tags
    ]
    vendidos = []
    for venta in sorted(
        (m for m in ctx["hasta_dia"] if m["kind"] == "venta"),
        key=lambda m: (_fecha(m["occurred_on"]), str(m["movement_id"])),
        reverse=True,
    ):
        tag = _un_animal(venta)
        estado = _estado(ctx, tag, por_tag.get(tag, []))
        compra = compras_por_tag.get(tag)
        vendida_el = _fecha(venta["occurred_on"])
        comprada_el = _fecha(compra["occurred_on"]) if compra else None
        vendidos.append(
            {
                "tag_id": tag,
                "vendida_el": vendida_el,
                "comprada_el": comprada_el,
                "dias_en_rancho": (vendida_el - comprada_el).days if comprada_el else None,
                "venta_mxn": _mxn(_frac(venta["amount_mxn"])),
                "costo_acumulado": estado["costo_acumulado"],
                "resultado": estado["resultado"],
            }
        )

    return {
        "desde": desde,
        "dia": dia,
        "precio": precio_vigente(ctx["hasta_dia"], dia),
        "mes": {
            "gastos_mxn": _de_centavos(sum(por_categoria.values())),
            "por_categoria": {k: _de_centavos(v) for k, v in sorted(por_categoria.items())},
            "sin_asignar_mxn": _de_centavos(sin_asignar),
            "compras_mxn": _de_centavos(sum(_centavos(_frac(m["amount_mxn"])) for m in compras)),
            "ventas_mxn": _de_centavos(
                sum(_centavos(_frac(m["amount_mxn"])) for m in ventas_mes)
            ),
            "fuente": {
                "movimientos": fuentes,
                "compras": [str(m["movement_id"]) for m in compras],
                "ventas": [str(m["movement_id"]) for m in ventas_mes],
            },
        },
        "animales": animales,
        "vendidos": vendidos,
    }


def para_json(valor: Any) -> Any:
    """Montos como texto (igual que #173) y fechas ISO, para no perder centavos en un float."""
    if isinstance(valor, Decimal):
        return str(valor)
    if isinstance(valor, datetime | date):
        return valor.isoformat()
    if isinstance(valor, Mapping):
        return {str(k): para_json(v) for k, v in valor.items()}
    if isinstance(valor, list | tuple):
        return [para_json(v) for v in valor]
    return valor
