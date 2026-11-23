#!/usr/bin/env python3
"""Siembra el rancho demo de cada cuenta real (016): pesajes, fichas, bitacora y dinero.

Cada cuenta real tiene, aparte, un rancho demo (`<slug>-demo`, `es_demo`) que
sus usuarios abren con el interruptor "Datos de demostracion" de la web. Lo
real que llegue de las basculas nunca se mezcla con esto: vive en otra
organizacion. Ver `apps/api/src/fierro_api/migrations/016_demo_orgs.sql`.

Por cuenta carga la historia de `seed_demo_hato.py` (38 animales con novedades
que el asistente sabe encontrar) mas lo que esa historia no trae:

- 4 novillos de finalizacion que se pesan hasta que se venden
- fichas con raza y embarque para todos, porque el dinero exige animal registrado
- compras por animal en 3 embarques, con peso y precio por kilo de becerro
- gastos: alimento por corral y mes, mano de obra y servicios del hato, flete y
  vacunacion por embarque, tratamientos ligados a su nota de bitacora, una
  reparacion, y una captura equivocada que se anula y se recaptura
- ventas de los finalizados con destare, y precio de mercado semanal
- notas del diario del rancho (embarques, insumos, equipo)

Todo es determinista: los ids salen de la semilla, la cuenta y `--hasta`.
Repetirlo no duplica nada. Para refrescar las fechas de una demo vieja usa
`--rehacer`, que purga el rancho demo y lo siembra de nuevo.

    export FIERRO_TOKEN=...   # llave de un superusuario
    python3 scripts/seed_demo_cuentas.py --api https://<api-de-stage> --todas
    python3 scripts/seed_demo_cuentas.py --api ... --org los-encinos --rehacer
    python3 scripts/seed_demo_cuentas.py --api ... --org los-encinos --purgar
    python3 scripts/seed_demo_cuentas.py --org los-encinos --out demo.json   # sin red

En production se detiene salvo `--permitir-produccion`. Solo stdlib.
"""

from __future__ import annotations

import argparse
import json
import os
import random
import sys
import urllib.error
import uuid
import zlib
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

from seed_demo_hato import (  # noqa: E402 - el import depende del path de arriba
    COUNTRY_CODE,
    NAMESPACE,
    SOURCE,
    ZACATECAS,
    Animal,
    Api,
    ErrorApi,
    _cuantiza,
    _q,
    estaciones,
    generar,
    hato,
    peso,
)

# Distinto de los otros generadores: un id de dinero nunca choca con un evento.
NAMESPACE_DINERO = uuid.UUID("7d1e4c52-0a6b-4c8e-b3f1-5e9a2d7c4b10")

RANCHO = ("corrales", "Corrales de engorda (demo)")
CORRAL = {"novillo": "Engorda", "vaquilla": "Recría"}
EMBARQUES_DIAS_ANTES = (45, 28, 12)  # dias antes de la primera jornada
SUBASTA = "la subasta de Fresnillo"


def semilla_cuenta(seed: int, org: str) -> int:
    """Una semilla por cuenta: mismos datos al repetir, distintos entre cuentas."""
    return zlib.crc32(f"{seed}|{org}".encode()) % 100_000


def _id(org: str, *partes: object) -> str:
    return str(uuid.uuid5(NAMESPACE_DINERO, "|".join([org, *map(str, partes)])))


def _dinero(valor: float) -> str:
    return f"{valor:.2f}"


def _a_las(dia: date, hora: int) -> str:
    return datetime(dia.year, dia.month, dia.day, hora, 0, tzinfo=ZACATECAS).isoformat()


def _vendidos(rng: random.Random, usados: set[str], semanas: int) -> list[dict[str, Any]]:
    """Novillos de finalizacion que salen vendidos a media ventana."""
    salida = []
    for i, jornada in enumerate((semanas // 3, semanas // 3 + 1, semanas // 2, semanas // 2 + 2)):
        while True:
            tag = f"{COUNTRY_CODE:03d}{rng.randrange(10**11, 10**12):012d}"
            if tag not in usados:
                break
        usados.add(tag)
        salida.append(
            {
                "animal": Animal(
                    f"vendido-{i + 1}", "novillo", rng.choice(("Beefmaster", "Brangus", "Angus")),
                    round(rng.uniform(425, 460)), round(rng.uniform(1.15, 1.3), 2),
                ),
                "tag": tag,
                "ultima_jornada": jornada,
            }
        )
    return salida


def generar_cuenta(*, seed: int, hasta: date, semanas: int, demo: str) -> dict[str, Any]:
    """Todo lo que se siembra en un rancho demo, sin tocar la red."""
    s = semilla_cuenta(seed, demo)
    base = generar(seed=s, hasta=hasta, semanas=semanas, org=demo)
    rng = random.Random(f"{s}|cuenta")
    fechas = [hasta - timedelta(days=7 * (semanas - 1 - j)) for j in range(semanas)]
    inicio = fechas[0]
    manga, _ = estaciones(demo)

    por_clave = {a.clave: a for a in hato(s)}
    tags: dict[str, str] = dict(base["aretes"])
    vendidos = _vendidos(rng, set(tags.values()), semanas)
    for v in vendidos:
        por_clave[v["animal"].clave] = v["animal"]
        tags[v["animal"].clave] = v["tag"]

    # Pesajes de los vendidos, hasta su ultima jornada.
    lecturas = list(base["readings"])
    ultimo_peso: dict[str, float] = {}
    for v in vendidos:
        animal = v["animal"]
        for j in range(v["ultima_jornada"] + 1):
            dia = fechas[j]
            r = random.Random(f"{s}|{demo}|{v['tag']}|{dia.isoformat()}")
            kg = _cuantiza(peso(animal, j, semanas) + r.gauss(0.0, 0.4))
            ultimo_peso[v["tag"]] = kg
            hora = datetime(dia.year, dia.month, dia.day, r.randrange(7, 11),
                            r.randrange(60), tzinfo=ZACATECAS)
            lecturas.append(
                {
                    "event_id": str(uuid.uuid5(NAMESPACE, f"{demo}|{v['tag']}|{dia.isoformat()}")),
                    "device_id": manga,
                    "tag_id": v["tag"],
                    "weight_kg": kg,
                    "captured_at": hora.isoformat(),
                    "stable": True,
                    "source": SOURCE,
                }
            )
    lecturas.sort(key=lambda x: (x["captured_at"], x["event_id"]))

    # Embarques: cada animal llega en uno, antes de su primer pesaje.
    llegada: dict[str, date] = {}
    embarques: list[list[str]] = [[] for _ in EMBARQUES_DIAS_ANTES]
    for clave, animal in por_clave.items():
        if animal.sin_pesaje:
            llegada[clave] = hasta - timedelta(days=4)
            continue
        k = 0 if clave.startswith("vendido") else rng.randrange(len(EMBARQUES_DIAS_ANTES))
        embarques[k].append(clave)
        llegada[clave] = inicio - timedelta(days=EMBARQUES_DIAS_ANTES[k])
    ultimo_embarque = [c for c, a in por_clave.items() if a.sin_pesaje]

    vendido_en = {v["animal"].clave: fechas[v["ultima_jornada"]] + timedelta(days=2)
                  for v in vendidos}

    fichas = []
    for clave, animal in por_clave.items():
        notas = animal.notas or (
            f"{animal.raza}. Llegó el {llegada[clave].isoformat()} de {SUBASTA}."
        )
        if clave in vendido_en:
            notas = (f"{animal.raza}, lote de finalización. Vendido el "
                     f"{vendido_en[clave].isoformat()} a una engordadora de Fresnillo.")
        fichas.append({"tag_id": tags[clave], "alias": animal.alias, "notes": notas,
                       "corral": CORRAL[animal.grupo]})

    diario: list[dict[str, Any]] = []
    movimientos: list[dict[str, Any]] = []
    anulaciones: list[dict[str, Any]] = []

    def nota(clave: str, dia: date, categoria: str, texto: str,
             animales: list[str] | None = None) -> str:
        entry_id = _id(demo, "diario", clave)
        diario.append({"entry_id": entry_id, "occurred_at": _a_las(dia, 13),
                       "category": categoria, "body": texto,
                       "animals": [tags[c] for c in animales or []]})
        return entry_id

    def gasto(clave: str, dia: date, categoria: str, monto: float, *, alcance: str,
              corral: str | None = None, animales: list[str] | None = None,
              periodo: tuple[date, date] | None = None, origen: str | None = None) -> str:
        mov_id = _id(demo, "gasto", clave)
        movimientos.append({
            "movement_id": mov_id, "kind": "gasto", "category": categoria,
            "amount_mxn": _dinero(monto), "occurred_on": dia.isoformat(),
            "period_start": periodo[0].isoformat() if periodo else None,
            "period_end": periodo[1].isoformat() if periodo else None,
            "scope": alcance, "corral": corral, "source_entry_id": origen,
            "animals": sorted(tags[c] for c in animales or []),
        })
        return mov_id

    # Compras, flete y vacunacion por embarque.
    for k, claves in enumerate([*embarques, ultimo_embarque]):
        if not claves:
            continue
        dia = llegada[claves[0]]
        entrada = nota(f"embarque-{k}", dia, "manejo",
                       f"Llegó embarque de {len(claves)} cabezas de {SUBASTA}. "
                       "Se aretaron y se pasaron a su corral.", claves)
        gasto(f"flete-{k}", dia, "transporte", 3800 + 140 * len(claves),
              alcance="animales", animales=claves, origen=entrada)
        vacuna = nota(f"vacuna-{k}", dia + timedelta(days=1), "salud",
                      "Vacuna clostridial, desparasitante y vitaminas A-D-E al embarque.", claves)
        gasto(f"vacuna-{k}", dia + timedelta(days=1), "sanidad", 185 * len(claves),
              alcance="animales", animales=claves, origen=vacuna)
        for clave in claves:
            animal = por_clave[clave]
            dias_previos = (inicio - dia).days
            kg = (rng.uniform(215, 245) if animal.sin_pesaje
                  else max(170.0, animal.peso_inicial - animal.ganancia * dias_previos))
            # El kilo de becerro ligero vale mas que el de un novillo ya pesado.
            if kg >= 350:
                precio = rng.uniform(54, 57)
            elif animal.grupo == "novillo":
                precio = rng.uniform(66, 74)
            else:
                precio = rng.uniform(58, 66)
            kg = _cuantiza(kg)
            movimientos.append({
                "movement_id": _id(demo, "compra", tags[clave]), "kind": "compra",
                "amount_mxn": _dinero(kg * round(precio, 2)), "weight_kg": _dinero(kg),
                "occurred_on": dia.isoformat(), "scope": "animales",
                "animals": [tags[clave]],
            })

    # Ventas de los finalizados: peso de la ultima jornada con 4% de destare.
    for v in vendidos:
        clave = v["animal"].clave
        dia = vendido_en[clave]
        kg = _cuantiza(ultimo_peso[v["tag"]] * 0.96)
        precio = round(rng.uniform(56, 59), 2)  # ganado gordo de primera
        movimientos.append({
            "movement_id": _id(demo, "venta", v["tag"]), "kind": "venta",
            "amount_mxn": _dinero(kg * precio), "weight_kg": _dinero(kg),
            "occurred_on": dia.isoformat(), "scope": "animales", "animals": [v["tag"]],
        })
        gasto(f"flete-venta-{clave}", dia, "transporte", 1200, alcance="animales",
              animales=[clave])

    # Gastos por mes: alimento por corral, un vaquero y luz de la bomba del hato.
    primero = min(llegada.values())
    mes = primero.replace(day=1)
    while mes <= hasta:
        siguiente = (mes + timedelta(days=32)).replace(day=1)
        desde, fin = max(mes, primero), min(siguiente - timedelta(days=1), hasta)
        dias = (fin - desde).days + 1
        clave_mes = mes.strftime("%Y-%m")
        for grupo, costo_dia in (("novillo", rng.uniform(48, 55)),
                                 ("vaquilla", rng.uniform(28, 33))):
            cabezas_dia = sum(
                max(0, (min(fin, vendido_en.get(c, fin)) - max(desde, llegada[c])).days + 1)
                for c, a in por_clave.items() if a.grupo == grupo
            )
            if cabezas_dia:
                gasto(f"alimento-{grupo}-{clave_mes}", fin, "alimento", cabezas_dia * costo_dia,
                      alcance="corral", corral=CORRAL[grupo], periodo=(desde, fin))
        gasto(f"vaquero-{clave_mes}", fin, "mano_obra", 3800 * dias / 7,
              alcance="hato", periodo=(desde, fin))
        gasto(f"luz-{clave_mes}", fin, "otros", rng.uniform(1150, 1650),
              alcance="hato", periodo=(desde, fin))
        mes = siguiente

    insumos = nota("insumos", inicio + timedelta(days=3), "insumos",
                   "Llegaron 12 t de rastrojo de maíz y 8 t de maíz rolado.")
    del insumos  # el alimento se paga por mes y corral, no por esta entrega
    reparacion = nota("comederos", inicio + timedelta(days=30), "equipo",
                      "Se soldaron dos comederos del corral de engorda y se cambió el flotador "
                      "del bebedero.")
    gasto("comederos", inicio + timedelta(days=30), "instalaciones", 7800, alcance="hato",
          origen=reparacion)

    # Tratamientos, ligados a su nota de bitacora.
    for clave, monto, pista in (("enfermo", 1850, "neumonía"), ("coja", 380, "espina")):
        apunte: dict[str, Any] = next(e for e in base["bitacora"]
                                      if e["tag_id"] == tags[clave] and pista in e["body"])
        dia = date.fromisoformat(apunte["occurred_at"][:10])
        gasto(f"tratamiento-{clave}", dia, "sanidad", monto, alcance="animales",
              animales=[clave], origen=apunte["entry_id"])

    # Una captura equivocada: se anula y se recaptura bien.
    dia = inicio + timedelta(days=40)
    equivocado = gasto("veterinario-error", dia, "sanidad", 15600, alcance="hato")
    anulaciones.append({"movement_id": _id(demo, "anula", "veterinario-error"),
                        "anula": equivocado, "occurred_on": (dia + timedelta(days=1)).isoformat()})
    gasto("veterinario", dia, "sanidad", 1560, alcance="hato")

    # Precio de mercado semanal del ganado en pie, con tendencia suave.
    precio = rng.uniform(51.5, 54.0)
    for dia in fechas:
        precio = min(62.0, max(48.0, precio + rng.gauss(0.08, 0.35)))
        movimientos.append({
            "movement_id": _id(demo, "precio", dia.isoformat()), "kind": "precio_mercado",
            "precio_kg_mxn": _dinero(precio), "occurred_on": dia.isoformat(), "scope": "hato",
        })

    movimientos.sort(key=lambda m: (m["occurred_on"], m["movement_id"]))
    return {
        "demo": demo,
        "hasta": base["hasta"],
        "aretes": tags,
        "readings": lecturas,
        "fichas": fichas,
        "bitacora": base["bitacora"],
        "diario": diario,
        "movimientos": movimientos,
        "anulaciones": anulaciones,
    }


# ---------------------------------------------------------------------------
# Red
# ---------------------------------------------------------------------------


def _comprobar_entorno(api: Api, permitir_produccion: bool) -> None:
    entorno = api("GET", "/health").get("env")
    print(f"API {api.base}  entorno={entorno}")
    if entorno == "production" and not permitir_produccion:
        raise SystemExit(
            "La API es de production. Los ranchos demo viven aparte de los reales, pero "
            "sembrarlos aqui necesita el OK explicito: usa --permitir-produccion."
        )
    if not api("GET", "/v1/auth/me").get("is_superuser"):
        raise SystemExit("La llave no es de un superusuario: no puede crear ranchos demo.")


def cuentas_reales(arbol: list[dict[str, Any]]) -> list[str]:
    return [o["slug"] for o in arbol if not o.get("es_demo")]


def sembrar_cuenta(api: Api, org: str, *, seed: int, hasta: date, semanas: int,
                   rehacer: bool, lote: int = 200) -> None:
    if rehacer:
        try:
            print(f"{org}: purgado {api('DELETE', f'/v1/orgs/{_q(org)}/demo')['borrado']}")
        except ErrorApi as exc:
            if "no tiene rancho demo" not in exc.detalle:
                raise
    demo = api("POST", f"/v1/orgs/{_q(org)}/demo")["slug"]
    datos = generar_cuenta(seed=seed, hasta=hasta, semanas=semanas, demo=demo)

    arbol = api("GET", "/v1/orgs")["orgs"]
    nodo = next(o for o in arbol if o["slug"] == demo)
    if not any(r["slug"] == RANCHO[0] for r in nodo["ranches"]):
        api("POST", f"/v1/orgs/{_q(demo)}/ranches", {"slug": RANCHO[0], "name": RANCHO[1]})
    duenos = {d["device_id"]: o["slug"] for o in arbol for r in o["ranches"] for d in r["devices"]}
    for estacion in estaciones(demo):
        if duenos.get(estacion, demo) != demo:
            raise SystemExit(f"La estacion {estacion} es de {duenos[estacion]}. No se mueve.")
        api("PUT", f"/v1/devices/{_q(estacion)}", {"org": demo, "ranch": RANCHO[0]})

    # Una sola historia por demo: pesajes de otra --hasta se mezclarian.
    nuestros = {r["event_id"] for r in datos["readings"]}
    muestra = datos["aretes"]["promedio"]
    previos = api("GET", f"/v1/animals/{_q(muestra)}/readings?org={_q(demo)}&limit=200")
    if any(r["event_id"] not in nuestros for r in previos["readings"]):
        raise SystemExit(f"{demo} ya tiene otra siembra. Usa --rehacer para refrescarla.")

    for inicio in range(0, len(datos["readings"]), lote):
        api("POST", "/v1/readings", {"readings": datos["readings"][inicio : inicio + lote]})
    for ficha in datos["fichas"]:
        api("PUT", f"/v1/animals/{_q(ficha['tag_id'])}?org={_q(demo)}",
            {"alias": ficha["alias"], "notes": ficha["notes"]})
    for entrada in datos["bitacora"]:
        cuerpo = {k: v for k, v in entrada.items() if k != "tag_id"}
        api("POST", f"/v1/animals/{_q(entrada['tag_id'])}/journal?org={_q(demo)}", cuerpo)
    for entrada in datos["diario"]:
        api("POST", f"/v1/journal?org={_q(demo)}", entrada)
    for mov in datos["movimientos"]:
        cuerpo = {k: v for k, v in mov.items() if v is not None}
        api("POST", f"/v1/dinero/movimientos?org={_q(demo)}", cuerpo)
    for anula in datos["anulaciones"]:
        api("POST", f"/v1/dinero/movimientos/{anula['anula']}/anular?org={_q(demo)}",
            {"movement_id": anula["movement_id"], "occurred_on": anula["occurred_on"]})
    print(
        f"{org} -> {demo}: {len(datos['fichas'])} animales, {len(datos['readings'])} pesajes, "
        f"{len(datos['movimientos'])} movimientos, {len(datos['diario'])} notas del diario"
    )


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    hoy = datetime.now(ZACATECAS).date()
    p = argparse.ArgumentParser(description="Siembra el rancho demo de cada cuenta.")
    p.add_argument("--api", help="URL de la API")
    p.add_argument("--token", default=os.getenv("FIERRO_TOKEN"),
                   help="Llave de un superusuario (o variable FIERRO_TOKEN)")
    p.add_argument("--org", action="append", default=[], help="Cuenta real; se puede repetir")
    p.add_argument("--todas", action="store_true", help="Todas las cuentas reales")
    p.add_argument("--rehacer", action="store_true", help="Purga el demo y lo siembra de nuevo")
    p.add_argument("--purgar", action="store_true", help="Solo purga el demo, no siembra")
    p.add_argument("--out", help="Escribir los datos como JSON en vez de enviarlos")
    p.add_argument("--hasta", type=date.fromisoformat, default=hoy - timedelta(days=1),
                   help="Fecha de la ultima jornada (AAAA-MM-DD). Por omision, ayer")
    p.add_argument("--semanas", type=int, default=14)
    p.add_argument("--seed", type=int, default=2026)
    p.add_argument("--timeout", type=float, default=60.0)
    p.add_argument("--permitir-produccion", action="store_true")
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if args.semanas < 8:
        print("--semanas debe ser al menos 8", file=sys.stderr)
        return 2
    if args.out:
        if len(args.org) != 1:
            print("--out necesita exactamente un --org", file=sys.stderr)
            return 2
        datos = generar_cuenta(seed=args.seed, hasta=args.hasta, semanas=args.semanas,
                               demo=f"{args.org[0]}-demo")
        Path(args.out).write_text(json.dumps(datos, indent=2, ensure_ascii=False), "utf-8")
        print(f"escrito {args.out}")
        return 0
    if not args.api or not args.token:
        print("Falta --api y --token (o FIERRO_TOKEN), o usa --out", file=sys.stderr)
        return 2
    if bool(args.org) == args.todas:
        print("Indica --org (una o varias) o --todas", file=sys.stderr)
        return 2

    api = Api(args.api, args.token, args.timeout)
    try:
        _comprobar_entorno(api, args.permitir_produccion)
        orgs = cuentas_reales(api("GET", "/v1/orgs")["orgs"]) if args.todas else args.org
        for org in orgs:
            if args.purgar:
                print(f"{org}: purgado {api('DELETE', f'/v1/orgs/{_q(org)}/demo')['borrado']}")
            else:
                sembrar_cuenta(api, org, seed=args.seed, hasta=args.hasta,
                               semanas=args.semanas, rehacer=args.rehacer)
    except ErrorApi as exc:
        print(f"La API respondio {exc}", file=sys.stderr)
        return 1
    except (urllib.error.URLError, OSError) as exc:
        print(f"No se pudo hablar con la API: {exc}", file=sys.stderr)
        return 1
    print("listo")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
