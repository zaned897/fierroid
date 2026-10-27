"""Cuentas del hato para el asistente (#110), con las reglas de la ficha.

Todo aqui es puro: recibe pesajes y fichas ya acotados a una organizacion y
devuelve numeros con la explicacion de que conto y que dejo fuera. Las reglas
son un port de `apps/web/src/animalTrend.js` (tendencia y atipicos) y de la
regla de "se quedo atras" de #95; los tests de paridad viven en
`tests/test_hato.py`. Si cambias una, cambia la otra.
"""

from __future__ import annotations

import math
from collections.abc import Iterable
from datetime import UTC, datetime
from statistics import median
from typing import Any

DAY_S = 86400.0

# Regla de #95: tantos pesajes seguidos ganando 1 kg o menos entre uno y otro.
# Es un punto de partida acordado en el panel, no un dato zootecnico.
REZAGO = {"pesajes": 2, "ganancia_kg": 1.0}


def _fecha(valor: Any) -> datetime | None:
    if not isinstance(valor, str):
        return None
    try:
        fecha = datetime.fromisoformat(valor.replace("Z", "+00:00"))
    except ValueError:
        return None
    return fecha if fecha.tzinfo else fecha.replace(tzinfo=UTC)


def _dia(punto: dict[str, Any]) -> float:
    return punto["_t"].timestamp() / DAY_S


def es_prueba(lectura: dict[str, Any]) -> bool:
    fuente = lectura.get("source") or ""
    return fuente in ("mock", "synthetic") or fuente.startswith("proto-")


def puntos_tendencia(lecturas: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    """Como `trendReadings`: estables, con peso y fecha validos, sin pruebas.

    Ordenados del mas viejo al mas nuevo y sin eventos repetidos.
    """
    unicos: dict[str, dict[str, Any]] = {}
    for lectura in lecturas:
        unicos[lectura["event_id"]] = lectura
    puntos = []
    for lectura in unicos.values():
        peso = lectura.get("weight_kg")
        fecha = _fecha(lectura.get("captured_at"))
        if (
            lectura.get("stable") is True
            and isinstance(peso, int | float)
            and math.isfinite(peso)
            and peso >= 0
            and fecha is not None
            and not es_prueba(lectura)
        ):
            puntos.append({**lectura, "_t": fecha})
    puntos.sort(key=lambda p: (p["_t"], p["event_id"]))
    return puntos


def ids_atipicos(puntos: list[dict[str, Any]], ventana: int = 3) -> set[str]:
    """Como `outlierIds`: pesajes que se apartan de sus vecinos. Se senalan, no se borran."""
    pendientes = [
        (b["weight_kg"] - a["weight_kg"]) / (_dia(b) - _dia(a))
        for j, a in enumerate(puntos)
        for b in puntos[j + 1 :]
        if _dia(b) != _dia(a)
    ]
    pendiente = median(pendientes) if pendientes else 0.0
    ids = set()
    for i, punto in enumerate(puntos):
        vecinos = puntos[max(0, i - ventana) : i] + puntos[i + 1 : i + 1 + ventana]
        if len(vecinos) < 3:
            continue
        esperado = median(v["weight_kg"] + pendiente * (_dia(punto) - _dia(v)) for v in vecinos)
        if abs(punto["weight_kg"] - esperado) > max(15, esperado * 0.07):
            ids.add(punto["event_id"])
    return ids


def ganancia_diaria(puntos: list[dict[str, Any]]) -> float | None:
    """Como `trendSummary().dailyKg`: solo con al menos un dia de por medio."""
    if len(puntos) < 2:
        return None
    dias = _dia(puntos[-1]) - _dia(puntos[0])
    return (puntos[-1]["weight_kg"] - puntos[0]["weight_kg"]) / dias if dias >= 1 else None


def _ultimo_por_dia(puntos: list[dict[str, Any]]) -> list[dict[str, Any]]:
    por_dia: dict[str, dict[str, Any]] = {}
    for punto in puntos:
        por_dia[punto["captured_at"][:10]] = punto
    return list(por_dia.values())


def pesajes_sin_ganar(
    puntos: list[dict[str, Any]], ganancia_kg: float = REZAGO["ganancia_kg"]
) -> int:
    """Intervalos seguidos, contando desde el ultimo, que ganaron ganancia_kg o menos."""
    dias = _ultimo_por_dia(puntos)
    cuenta = 0
    for i in range(len(dias) - 1, 0, -1):
        if dias[i]["weight_kg"] - dias[i - 1]["weight_kg"] > ganancia_kg:
            break
        cuenta += 1
    return cuenta


def _publico(punto: dict[str, Any] | None) -> dict[str, Any] | None:
    if punto is None:
        return None
    return {
        k: punto[k] for k in ("event_id", "captured_at", "weight_kg", "device_id") if k in punto
    }


def _por_arete(lecturas: Iterable[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    grupos: dict[str, list[dict[str, Any]]] = {}
    for lectura in lecturas:
        if lectura.get("tag_id"):
            grupos.setdefault(lectura["tag_id"], []).append(lectura)
    return grupos


def _animal(tag: str, lecturas: list[dict[str, Any]], ganancia_kg: float) -> dict[str, Any]:
    puntos = puntos_tendencia(lecturas)
    atipicos = ids_atipicos(puntos)
    limpios = [p for p in puntos if p["event_id"] not in atipicos]
    dias = _ultimo_por_dia(limpios)
    sin_ganar = pesajes_sin_ganar(limpios, ganancia_kg)
    return {
        "tag_id": tag,
        "puntos": puntos,
        "limpios": limpios,
        "ultimo": limpios[-1] if limpios else None,
        "ultimo_atipico": puntos[-1] if puntos and puntos[-1]["event_id"] in atipicos else None,
        "ganancia_diaria_kg": ganancia_diaria(limpios),
        "sin_ganar": sin_ganar,
        "kg_sin_ganar": dias[-1]["weight_kg"] - dias[-1 - sin_ganar]["weight_kg"]
        if sin_ganar
        else None,
        "comparable": len(dias) >= 2,
    }


def resumen_hato(
    lecturas: list[dict[str, Any]], fichas: list[dict[str, Any]], *, truncado: bool = False
) -> dict[str, Any]:
    """Cuantos animales hay y cuanto pesan, diciendo que cuenta y que no.

    El peso total es la suma del ultimo pesaje estable de cada animal. Si ese
    ultimo pesaje es atipico, el animal no entra: sumar un peso dudoso seria
    presentar como medido algo que la propia ficha marca para revisar.
    """
    grupos = _por_arete(lecturas)
    registrados = set(grupos) | {f["tag_id"] for f in fichas if f.get("tag_id")}
    sumados, atipicos, sin_estable = [], [], []
    for tag, filas in grupos.items():
        animal = _animal(tag, filas, REZAGO["ganancia_kg"])
        if animal["ultimo_atipico"]:
            atipicos.append(tag)
        elif animal["ultimo"]:
            sumados.append(animal["ultimo"])
        else:
            sin_estable.append(tag)
    mas_viejo = min(sumados, key=lambda p: p["_t"]) if sumados else None
    return {
        "animales_registrados": len(registrados),
        "animales_pesados": len(grupos),
        "con_ficha_sin_pesaje": sorted(registrados - set(grupos)),
        "peso_total_kg": round(sum(p["weight_kg"] for p in sumados), 1),
        "animales_en_el_total": len(sumados),
        "fuera_por_ultimo_pesaje_atipico": sorted(atipicos),
        "fuera_por_no_tener_pesaje_estable": sorted(sin_estable),
        "pesaje_mas_viejo_en_el_total": mas_viejo["captured_at"] if mas_viejo else None,
        "regla_del_total": (
            "Suma del último pesaje estable de cada animal, sin pruebas ni atípicos."
        ),
        "pesajes_revisados": len(lecturas),
        "lectura_incompleta": truncado,
    }


def animales_a_revisar(
    lecturas: list[dict[str, Any]],
    *,
    ahora: datetime,
    pesajes: int = REZAGO["pesajes"],
    dias_sin_pesar: int = 30,
    truncado: bool = False,
) -> dict[str, Any]:
    """Como `herdReview` de #95, mas los que no se pesan desde hace dias_sin_pesar."""
    animales = [
        _animal(tag, filas, REZAGO["ganancia_kg"]) for tag, filas in _por_arete(lecturas).items()
    ]
    atras = sorted(
        (a for a in animales if a["comparable"] and a["sin_ganar"] >= pesajes),
        key=lambda a: (-a["sin_ganar"], a["kg_sin_ganar"]),
    )
    tags_atras = {a["tag_id"] for a in atras}
    resto = [
        a["ganancia_diaria_kg"]
        for a in animales
        if a["comparable"] and a["tag_id"] not in tags_atras and a["ganancia_diaria_kg"] is not None
    ]
    con_ganancia = sorted(
        (a for a in animales if a["comparable"] and a["ganancia_diaria_kg"] is not None),
        key=lambda a: a["ganancia_diaria_kg"],
    )
    limite = ahora.timestamp() - dias_sin_pesar * DAY_S
    viejos = sorted(
        (a for a in animales if a["puntos"] and a["puntos"][-1]["_t"].timestamp() < limite),
        key=lambda a: a["puntos"][-1]["_t"],
    )
    return {
        "sin_ganar_peso": [
            {
                "tag_id": a["tag_id"],
                "pesajes_sin_ganar": a["sin_ganar"],
                "kg_en_esos_pesajes": round(a["kg_sin_ganar"], 1),
                "ultimo": _publico(a["ultimo"]),
            }
            for a in atras
        ],
        "ganancia_mas_baja": (
            {
                "tag_id": con_ganancia[0]["tag_id"],
                "ganancia_diaria_kg": round(con_ganancia[0]["ganancia_diaria_kg"], 2),
            }
            if con_ganancia
            else None
        ),
        "ultimo_pesaje_atipico": [
            {"tag_id": a["tag_id"], "pesaje": _publico(a["ultimo_atipico"])}
            for a in animales
            if a["ultimo_atipico"]
        ],
        "sin_pesar": [
            {"tag_id": a["tag_id"], "ultimo_pesaje": a["puntos"][-1]["captured_at"]} for a in viejos
        ],
        "ganancia_mediana_del_resto_kg_dia": round(median(resto), 2) if resto else None,
        "animales_comparables": sum(1 for a in animales if a["comparable"]),
        "regla": (
            f"Sin ganar = {pesajes} pesajes seguidos ganando {REZAGO['ganancia_kg']:g} kg o menos "
            "entre uno y otro (un pesaje por día). Sin pruebas, inestables ni atípicos. "
            f"Sin pesar = más de {dias_sin_pesar} días desde su último pesaje estable."
        ),
        "pesajes_revisados": len(lecturas),
        "lectura_incompleta": truncado,
    }


def ficha_animal(
    lecturas: list[dict[str, Any]], fichas: list[dict[str, Any]], tag_id: str
) -> dict[str, Any] | None:
    filas = [lectura for lectura in lecturas if lectura.get("tag_id") == tag_id]
    ficha = next((f for f in fichas if f.get("tag_id") == tag_id), None)
    if not filas and ficha is None:
        return None
    animal = _animal(tag_id, filas, REZAGO["ganancia_kg"])
    atipicos = {p["event_id"] for p in animal["puntos"]} - {
        p["event_id"] for p in animal["limpios"]
    }
    return {
        "tag_id": tag_id,
        "alias": ficha.get("alias") if ficha else None,
        "notas": ficha.get("notes") if ficha else None,
        "pesajes_estables": [
            {**_publico(p), "atipico": p["event_id"] in atipicos} for p in animal["puntos"][-20:]
        ],
        "pesajes_totales": len(filas),
        "ganancia_diaria_kg": (
            round(animal["ganancia_diaria_kg"], 2)
            if animal["ganancia_diaria_kg"] is not None
            else None
        ),
        "pesajes_sin_ganar": animal["sin_ganar"],
    }


def buscar_animales(
    lecturas: list[dict[str, Any]],
    fichas: list[dict[str, Any]],
    *,
    texto: str | None = None,
    peso_min_kg: float | None = None,
    peso_max_kg: float | None = None,
    limite: int = 50,
) -> dict[str, Any]:
    """Por arete o alias, y por rango del ultimo peso limpio."""
    grupos = _por_arete(lecturas)
    alias = {f["tag_id"]: f.get("alias") for f in fichas if f.get("tag_id")}
    encontrados = []
    for tag in sorted(set(grupos) | set(alias)):
        nombre = alias.get(tag)
        if (
            texto
            and texto.lower() not in tag.lower()
            and texto.lower() not in (nombre or "").lower()
        ):
            continue
        ultimo = _animal(tag, grupos.get(tag, []), REZAGO["ganancia_kg"])["ultimo"]
        peso = ultimo["weight_kg"] if ultimo else None
        if (peso_min_kg is not None or peso_max_kg is not None) and peso is None:
            continue
        if peso_min_kg is not None and peso < peso_min_kg:
            continue
        if peso_max_kg is not None and peso > peso_max_kg:
            continue
        encontrados.append({"tag_id": tag, "alias": nombre, "ultimo": _publico(ultimo)})
    return {
        "animales": encontrados[:limite],
        "total": len(encontrados),
        "recortado": len(encontrados) > limite,
    }
