#!/usr/bin/env python3
"""Siembra un rancho de demostracion para "Preguntale a tu hato" (#110).

`seed_synthetic.py` marca sus pesajes como `source="synthetic"`, y el
asistente los descarta a proposito (`hato.es_prueba`): nunca presenta pruebas
como si fueran del ganado. Para enseñarlo en vivo hace falta un rancho cuyos
pesajes si cuenten. Este script lo crea completo, en una organizacion propia y
rotulada como demo, con una historia escrita para que cada herramienta del
asistente tenga algo que encontrar:

- novillos y vaquillas en recria y engorda, en El Mezquite, Fresnillo, Zac.
- dos que dejaron de ganar peso (uno enfermo, una coja), con su bitacora
- uno cuyo ultimo pesaje es atipico (se subieron dos a la bascula)
- dos que no se pesan desde hace mas de 30 dias (se fueron a otro potrero)
- uno con solo pesajes inestables y dos con ficha que todavia no se pesan

Todo pasa por la API publica, con la llave de un superusuario, en este orden:
organizacion -> rancho -> estaciones -> pesajes -> fichas -> bitacora -> usuario.
Registrar las estaciones antes de mandar pesajes evita lecturas invisibles.

    python3 scripts/seed_demo_hato.py --api https://<api-de-stage> --token "$FIERRO_TOKEN" \\
        --usuario demo.fierro@gmail.com
    python3 scripts/seed_demo_hato.py --out demo.json      # sin red: ver los datos

Es idempotente: event_id, entry_id y aretes salen de la semilla, el rancho y la
fecha de la ultima jornada (`--hasta`). Repetirlo no duplica nada. Sembrar el
mismo rancho con otra fecha mezclaria dos historias, y eso se detiene con error.

Solo stdlib, como seed_synthetic.py.
"""

from __future__ import annotations

import argparse
import json
import os
import random
import sys
import urllib.error
import urllib.parse
import urllib.request
import uuid
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from typing import Any

# Distinto del de seed_synthetic: un evento demo nunca choca con uno sintetico.
NAMESPACE = uuid.UUID("2b0f5c1e-6a43-4f7e-9d0a-7f3c1e5a9b21")

# Se cuenta en el asistente; "synthetic", "mock" y "proto-*" no. Ver hato.es_prueba.
SOURCE = "demo"

# Zacatecas no usa horario de verano desde 2022: UTC-6 todo el año.
ZACATECAS = timezone(timedelta(hours=-6))

SCALE_DIVISION_KG = 0.5
COUNTRY_CODE = 484

ORG = ("demo-el-mezquite", "Rancho El Mezquite (demo)")
RANCHO = ("el-mezquite", "El Mezquite, Fresnillo, Zac.")


def estaciones(org: str) -> tuple[str, str]:
    """Manga y corral. Llevan el slug: una estacion es de un solo rancho."""
    return f"{org}-manga", f"{org}-corral"


@dataclass(frozen=True)
class Animal:
    clave: str  # nombre interno de la historia; no viaja a la API
    grupo: str  # "novillo" o "vaquilla"
    raza: str
    peso_inicial: float  # kg en la primera jornada de la ventana
    ganancia: float  # kg/dia mientras todo va bien
    alias: str | None = None
    notas: str | None = None
    # Historia: cuantas jornadas antes de la ultima empieza el problema.
    estanca_desde: int | None = None
    ganancia_estancada: float = 0.0
    ultima_jornada: int = 0  # 0 = se peso en la ultima; 6 = hace 6 semanas
    ultimo_atipico: bool = False
    atipico_en: int | None = None  # una jornada vieja con lectura equivocada
    solo_inestables: bool = False
    jornadas: int | None = None  # cuantas jornadas lleva pesandose (None = todas)
    sin_pesaje: bool = False


RAZAS_NOVILLO = ("Beefmaster", "Charolais x Cebú", "Brangus", "Simmental x Cebú", "Angus")
RAZAS_VAQUILLA = ("Beefmaster", "Brangus", "Simmental x Cebú")

# Las que cuentan algo. El resto del hato crece normal y no tiene alias.
HISTORIAS: tuple[Animal, ...] = (
    Animal(
        "enfermo", "novillo", "Charolais x Cebú", 285, 1.0, alias="El Pinto",
        notas="Novillo Charolais x Cebú, comprado en la subasta de Fresnillo en julio.",
        estanca_desde=4, ganancia_estancada=-0.3,
    ),
    Animal(
        "coja", "vaquilla", "Brangus", 262, 0.55, alias="La Güera",
        notas="Vaquilla de reemplazo, hija de la vaca 17.",
        estanca_desde=3, ganancia_estancada=-0.1,
    ),
    Animal(
        "atipico", "novillo", "Beefmaster", 300, 1.05, alias="Canelo",
        notas="Novillo Beefmaster del lote de engorda.", ultimo_atipico=True,
    ),
    Animal(
        "potrero", "vaquilla", "Simmental x Cebú", 255, 0.6, alias="La Mora",
        notas="Vaquilla Simmental x Cebú.", ultima_jornada=6,
    ),
    Animal("potrero2", "vaquilla", "Beefmaster", 248, 0.55, ultima_jornada=5),
    Animal(
        "nervioso", "novillo", "Brangus", 270, 0.9, alias="El Prieto",
        notas="Muy nervioso en la manga.", solo_inestables=True, jornadas=2,
    ),
    Animal(
        "nuevo", "vaquilla", "Beefmaster", 0, 0, alias="Lucero",
        notas="Llegó en el último embarque de la subasta de Fresnillo. Falta pesarla.",
        sin_pesaje=True,
    ),
    Animal(
        "nuevo2", "novillo", "Angus", 0, 0,
        notas="Llegó en el último embarque. Falta pesarlo.", sin_pesaje=True,
    ),
    Animal(
        "estrella", "novillo", "Charolais x Cebú", 340, 1.25, alias="El Güero",
        notas="El mejor de la engorda. Candidato a venta en noviembre.", atipico_en=7,
    ),
    Animal(
        "pesado", "novillo", "Simmental x Cebú", 352, 1.15, alias="Tornado",
        notas="Novillo Simmental x Cebú, lote de finalización.",
    ),
    Animal(
        "pesado2", "novillo", "Beefmaster", 345, 1.1, alias="El Colorado",
        notas="Lote de finalización.",
    ),
    Animal(
        "promedio", "vaquilla", "Brangus", 268, 0.62, alias="La Pinta",
        notas="Vaquilla de reemplazo, mansa.",
    ),
)

BITACORA: dict[str, list[tuple[int, str, str]]] = {
    # (dias antes de la ultima jornada, categoria, texto)
    "enfermo": [
        (26, "salud", "Tose y no se arrima al comedero. Se apartó al corral de enfermería."),
        (25, "salud", "El veterinario lo revisó: neumonía. Tratamiento de cinco días."),
        (12, "observacion", "Ya come, pero sigue flaco. Revisar en la siguiente jornada."),
    ],
    "coja": [
        (20, "observacion", "Cojea de la pata trasera izquierda."),
        (19, "manejo", "Se le revisó la pezuña; tenía una espina. Se curó y se dejó en el corral."),
    ],
    "atipico": [
        (0, "manejo", "En la última jornada se subieron dos becerros juntos a la plataforma."),
    ],
    "potrero": [
        (42, "manejo", "Se movió con otras vaquillas al potrero de La Mesa; ahí no hay manga."),
    ],
    "estrella": [
        (30, "alimentacion", "Pasa a dieta de finalización: 70% grano, 30% rastrojo de maíz."),
    ],
    "pesado": [
        (30, "alimentacion", "Pasa a dieta de finalización: 70% grano, 30% rastrojo de maíz."),
    ],
}


def hato(seed: int, novillos: int = 18, vaquillas: int = 8) -> list[Animal]:
    """Las historias mas el resto del hato, que crece sin novedad."""
    rng = random.Random(f"{seed}|hato")
    resto = [
        Animal(
            f"novillo-{i + 1}", "novillo", rng.choice(RAZAS_NOVILLO),
            round(rng.uniform(235, 330)), round(rng.uniform(0.8, 1.15), 2),
        )
        for i in range(novillos)
    ] + [
        Animal(
            f"vaquilla-{i + 1}", "vaquilla", rng.choice(RAZAS_VAQUILLA),
            round(rng.uniform(230, 290)), round(rng.uniform(0.5, 0.7), 2),
        )
        for i in range(vaquillas)
    ]
    return [*HISTORIAS, *resto]


def aretes(seed: int, animales: list[Animal]) -> dict[str, str]:
    """Arete ISO 11784 por clave: 484 + 12 digitos, sin repetir."""
    rng = random.Random(f"{seed}|aretes")
    salida: dict[str, str] = {}
    usados: set[str] = set()
    for animal in animales:
        while True:
            tag = f"{COUNTRY_CODE:03d}{rng.randrange(10**11, 10**12):012d}"
            if tag not in usados:
                break
        usados.add(tag)
        salida[animal.clave] = tag
    return salida


def peso(animal: Animal, jornada: int, total: int) -> float:
    """Peso verdadero en la jornada `jornada` (0 = la primera de la ventana)."""
    dias = jornada * 7
    if animal.estanca_desde is None:
        return animal.peso_inicial + animal.ganancia * dias
    quiebre = (total - 1 - animal.estanca_desde) * 7
    if dias <= quiebre:
        return animal.peso_inicial + animal.ganancia * dias
    return (
        animal.peso_inicial
        + animal.ganancia * quiebre
        + animal.ganancia_estancada * (dias - quiebre)
    )


def _cuantiza(kg: float) -> float:
    return round(round(kg / SCALE_DIVISION_KG) * SCALE_DIVISION_KG, 1)


def generar(
    *, seed: int, hasta: date, semanas: int, org: str = ORG[0]
) -> dict[str, Any]:
    """Todo lo que se va a sembrar, sin tocar la red."""
    animales = hato(seed)
    tags = aretes(seed, animales)
    fechas = [hasta - timedelta(days=7 * (semanas - 1 - j)) for j in range(semanas)]

    lecturas: list[dict[str, Any]] = []
    for animal in animales:
        if animal.sin_pesaje:
            continue
        tag = tags[animal.clave]
        for j, dia in enumerate(fechas):
            atras = semanas - 1 - j
            if atras < animal.ultima_jornada:
                continue
            if animal.jornadas is not None and atras >= animal.jornadas:
                continue
            rng = random.Random(f"{seed}|{org}|{tag}|{dia.isoformat()}")
            # Uno de cada doce se queda sin arrear, salvo en las jornadas que
            # sostienen una historia: la ultima, y las del estancamiento.
            critica = atras <= max(animal.ultima_jornada, animal.estanca_desde or 0)
            if not critica and rng.random() < 1 / 12:
                continue
            kg = peso(animal, j, semanas) + rng.gauss(0.0, 0.4)
            if (animal.ultimo_atipico and atras == 0) or animal.atipico_en == atras:
                kg *= 1.2  # dos animales en la plataforma
            local = datetime(
                dia.year, dia.month, dia.day,
                rng.randrange(7, 13), rng.randrange(0, 60), rng.randrange(0, 60),
                tzinfo=ZACATECAS,
            )
            captured = local.astimezone(timezone.utc).isoformat()
            manga, corral = estaciones(org)
            device = manga if animal.grupo == "novillo" else corral
            lecturas.append(
                {
                    "event_id": str(uuid.uuid5(NAMESPACE, f"{org}|{tag}|{dia.isoformat()}")),
                    "device_id": device,
                    "tag_id": tag,
                    "weight_kg": _cuantiza(kg),
                    "captured_at": captured,
                    "stable": not animal.solo_inestables,
                    "source": SOURCE,
                }
            )
    lecturas.sort(key=lambda r: (r["captured_at"], r["event_id"]))

    fichas = [
        {"tag_id": tags[a.clave], "alias": a.alias, "notes": a.notas}
        for a in animales
        if a.alias or a.notas
    ]
    bitacora = []
    for clave, entradas in BITACORA.items():
        for dias_antes, categoria, texto in entradas:
            cuando = datetime(
                hasta.year, hasta.month, hasta.day, 14, 0, tzinfo=ZACATECAS
            ) - timedelta(days=dias_antes)
            bitacora.append(
                {
                    "tag_id": tags[clave],
                    "entry_id": str(
                        uuid.uuid5(NAMESPACE, f"{org}|{tags[clave]}|{dias_antes}|{texto}")
                    ),
                    "occurred_at": cuando.isoformat(),
                    "category": categoria,
                    "body": texto,
                }
            )
    return {
        "hasta": hasta.isoformat(),
        "aretes": {a.clave: tags[a.clave] for a in animales},
        "readings": lecturas,
        "fichas": fichas,
        "bitacora": bitacora,
    }


# ---------------------------------------------------------------------------
# Red
# ---------------------------------------------------------------------------


class ErrorApi(RuntimeError):
    def __init__(self, status: int, detalle: str) -> None:
        super().__init__(f"{status}: {detalle}")
        self.status = status
        self.detalle = detalle


class Api:
    def __init__(self, base: str, token: str | None, timeout: float) -> None:
        self.base = base.rstrip("/")
        self.token = token
        self.timeout = timeout

    def __call__(self, metodo: str, ruta: str, cuerpo: Any = None) -> Any:
        datos = json.dumps(cuerpo).encode("utf-8") if cuerpo is not None else None
        encabezados = {"Content-Type": "application/json"}
        if self.token:
            encabezados["Authorization"] = f"Bearer {self.token}"
        pedido = urllib.request.Request(
            self.base + ruta, data=datos, headers=encabezados, method=metodo
        )
        try:
            with urllib.request.urlopen(pedido, timeout=self.timeout) as respuesta:
                return json.load(respuesta)
        except urllib.error.HTTPError as exc:
            cuerpo_error = exc.read().decode("utf-8", "replace")
            try:
                detalle = json.loads(cuerpo_error).get("detail", cuerpo_error)
            except ValueError:
                detalle = cuerpo_error
            raise ErrorApi(exc.code, str(detalle)) from exc


def _q(texto: str) -> str:
    return urllib.parse.quote(texto, safe="")


def sembrar(
    api: Api,
    datos: dict[str, Any],
    *,
    org: str,
    org_nombre: str,
    usuario: str | None,
    permitir_produccion: bool,
    lote: int = 200,
) -> None:
    entorno = api("GET", "/health").get("env")
    print(f"API {api.base}  entorno={entorno}")
    if entorno == "production" and not permitir_produccion:
        raise SystemExit(
            "La API es de production, donde viven datos reales. "
            "El rancho demo va a stage; si de verdad lo quieres aqui, usa --permitir-produccion."
        )

    yo = api("GET", "/v1/auth/me")
    if not yo.get("is_superuser"):
        raise SystemExit("La llave no es de un superusuario: no puede crear el rancho.")
    if usuario and usuario.strip().lower() == str(yo.get("email", "")).lower():
        # create_user es upsert por correo: darte de alta en el rancho te quitaria
        # el superusuario. Mejor detenerse que dejarte sin panel de administracion.
        raise SystemExit(
            "--usuario no puede ser tu propio correo: te quitaria el superusuario. "
            "Usa otra cuenta de Google para la demo."
        )

    # 1. Organizacion y rancho, solo si faltan.
    arbol = api("GET", "/v1/orgs")["orgs"]
    existente = next((o for o in arbol if o["slug"] == org), None)
    if existente is None:
        api("POST", "/v1/orgs", {"slug": org, "name": org_nombre})
        print(f"organizacion creada: {org}")
    if existente is None or not any(r["slug"] == RANCHO[0] for r in existente["ranches"]):
        api("POST", f"/v1/orgs/{org}/ranches", {"slug": RANCHO[0], "name": RANCHO[1]})
        print(f"rancho creado: {RANCHO[0]}")

    # 2. Estaciones, antes que cualquier pesaje. Se revisa antes de moverlas:
    # mover una estacion ajena arrastraria la historia de otro rancho.
    duenos = {
        d["device_id"]: o["slug"]
        for o in arbol
        for r in o["ranches"]
        for d in r["devices"]
    }
    for estacion in estaciones(org):
        if duenos.get(estacion, org) != org:
            raise SystemExit(
                f"La estacion {estacion} es de {duenos[estacion]}. No se mueve: "
                "se llevaria sus pesajes. Usa otro --org."
            )
        api("PUT", f"/v1/devices/{estacion}", {"org": org, "ranch": RANCHO[0]})

    # 3. Una sola historia por rancho: si ya hay pesajes de otra --hasta, se mezclarian.
    nuestros = {r["event_id"] for r in datos["readings"]}
    muestra = datos["aretes"]["promedio"]
    previos = api("GET", f"/v1/animals/{muestra}/readings?org={_q(org)}&limit=200")["readings"]
    ajenos = [r for r in previos if r["event_id"] not in nuestros]
    if ajenos:
        fecha = max(r["captured_at"] for r in previos)[:10]
        raise SystemExit(
            f"{org} ya tiene pesajes de otra siembra (el mas nuevo es del {fecha}). "
            "Repite con esa --hasta, o siembra otro rancho con --org."
        )

    # 4. Pesajes, por lotes. El ingest es idempotente por event_id.
    duplicados = 0
    lecturas = datos["readings"]
    for inicio in range(0, len(lecturas), lote):
        respuesta = api("POST", "/v1/readings", {"readings": lecturas[inicio : inicio + lote]})
        duplicados += len(respuesta.get("duplicate_ids", []))
    print(f"pesajes: {len(lecturas)} enviados, {duplicados} ya estaban")

    # 5. Fichas y bitacora.
    for ficha in datos["fichas"]:
        api(
            "PUT",
            f"/v1/animals/{_q(ficha['tag_id'])}?org={_q(org)}",
            {"alias": ficha["alias"], "notes": ficha["notes"]},
        )
    print(f"fichas: {len(datos['fichas'])}")
    for entrada in datos["bitacora"]:
        cuerpo = {k: v for k, v in entrada.items() if k != "tag_id"}
        api("POST", f"/v1/animals/{_q(entrada['tag_id'])}/journal?org={_q(org)}", cuerpo)
    print(f"bitacora: {len(datos['bitacora'])} anotaciones")

    # 6. La cuenta con la que se hace la demo. El superusuario no puede: el
    # asistente necesita saber de que rancho hablar, y la PWA no se lo dice.
    if usuario:
        api("POST", "/v1/users", {"email": usuario, "org": org, "full_name": "Demo El Mezquite"})
        print(f"usuario {usuario} dado de alta en {org}: entra con Google con esa cuenta")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    hoy = datetime.now(ZACATECAS).date()
    parser = argparse.ArgumentParser(description="Siembra el rancho demo del asistente.")
    parser.add_argument("--api", help="URL de la API, p.ej. https://fierro-api-stage-...run.app")
    parser.add_argument(
        "--token",
        default=os.getenv("FIERRO_TOKEN"),
        help="Llave de un superusuario (o variable FIERRO_TOKEN)",
    )
    parser.add_argument("--out", help="Escribir los datos como JSON en vez de enviarlos")
    parser.add_argument("--usuario", help="Correo de Google que entrara a la demo")
    parser.add_argument("--org", default=ORG[0], help="Slug de la organizacion demo")
    parser.add_argument("--org-nombre", default=ORG[1])
    parser.add_argument(
        "--hasta",
        type=date.fromisoformat,
        default=hoy - timedelta(days=1),
        help="Fecha de la ultima jornada (AAAA-MM-DD). Por omision, ayer",
    )
    parser.add_argument("--semanas", type=int, default=14, help="Jornadas semanales de historia")
    parser.add_argument("--seed", type=int, default=2026)
    parser.add_argument("--timeout", type=float, default=60.0)
    parser.add_argument("--permitir-produccion", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if not args.api and not args.out:
        print("Falta --api o --out", file=sys.stderr)
        return 2
    if args.semanas < 8:
        # Con menos, los que no se pesan desde hace 6 semanas no tienen historia.
        print("--semanas debe ser al menos 8", file=sys.stderr)
        return 2

    datos = generar(seed=args.seed, hasta=args.hasta, semanas=args.semanas, org=args.org)
    print(
        f"rancho={args.org}  animales={len(datos['aretes'])}  pesajes={len(datos['readings'])}  "
        f"ultima jornada={datos['hasta']}"
    )
    if args.out:
        with open(args.out, "w", encoding="utf-8") as handle:
            json.dump(datos, handle, indent=2, ensure_ascii=False)
        print(f"escrito {args.out}")
    if args.api:
        if not args.token:
            print("Falta --token (o FIERRO_TOKEN): la llave de un superusuario", file=sys.stderr)
            return 2
        try:
            sembrar(
                Api(args.api, args.token, args.timeout),
                datos,
                org=args.org,
                org_nombre=args.org_nombre,
                usuario=args.usuario,
                permitir_produccion=args.permitir_produccion,
            )
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
