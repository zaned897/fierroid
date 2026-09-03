#!/usr/bin/env python3
"""Genera un hato sintetico y sus pesajes historicos.

Para que existe: la PWA y las consultas de la API necesitan meses de historia
para verse reales, y el MockHardware del agent solo produce el presente en
tiempo real. Esto llena el hueco sin inventar hardware.

Solo stdlib: corre con `python3` pelado dentro de un contenedor o en CI.

    python3 scripts/seed_synthetic.py --api http://127.0.0.1:8000 --animals 60 --days 120
    python3 scripts/seed_synthetic.py --out fixtures.json --animals 20 --days 30

Es idempotente: la misma --seed produce los mismos event_id, asi que repetir
el comando no duplica pesajes. Correrlo dos veces es la prueba mas barata de
que el ingest respeta la idempotencia.
"""

from __future__ import annotations

import argparse
import json
import math
import random
import sys
import urllib.error
import urllib.request
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

# ISO 3166 numerico de Mexico. En ISO 11784 son los 3 primeros digitos del arete.
DEFAULT_COUNTRY_CODE = 484

# Namespace fijo => event_id reproducible entre corridas.
EVENT_NAMESPACE = uuid.UUID("6f9619ff-8b86-d011-b42d-00c04fc964ff")

# Peso adulto (kg) por raza: (hembra, macho). Razas comunes en hato mexicano.
BREEDS: dict[str, tuple[float, float]] = {
    "Brahman": (520.0, 800.0),
    "Charolais": (750.0, 1100.0),
    "Angus": (550.0, 850.0),
    "Simmental": (700.0, 1000.0),
    "Beefmaster": (600.0, 900.0),
    "Cebu cruzado": (480.0, 720.0),
}

BIRTH_WEIGHT_KG = 36.0

# Division de escala tipica de un indicador de ganado (OIML R76): 0.5 kg.
SCALE_DIVISION_KG = 0.5


@dataclass(frozen=True)
class Animal:
    tag_id: str
    breed: str
    sex: str
    birth: datetime
    mature_kg: float
    vigor: float  # multiplicador individual: no todos crecen igual


def build_tag_id(rng: random.Random, country_code: int) -> str:
    """Arete ISO 11784: 3 digitos de pais + 12 de identificacion nacional."""
    national = rng.randrange(10**11, 10**12)
    return f"{country_code:03d}{national:012d}"


def build_herd(rng: random.Random, count: int, country_code: int, now: datetime) -> list[Animal]:
    herd: list[Animal] = []
    for _ in range(count):
        breed = rng.choice(list(BREEDS))
        sex = rng.choices(["F", "M"], weights=[0.75, 0.25])[0]  # hato de cria
        mature_female, mature_male = BREEDS[breed]
        mature = mature_female if sex == "F" else mature_male
        age_days = rng.randrange(60, 2200)  # de becerro destetado a vaca adulta
        herd.append(
            Animal(
                tag_id=build_tag_id(rng, country_code),
                breed=breed,
                sex=sex,
                birth=now - timedelta(days=age_days),
                mature_kg=mature * rng.uniform(0.92, 1.08),
                vigor=rng.uniform(0.9, 1.1),
            )
        )
    return herd


def weight_at(animal: Animal, when: datetime) -> float:
    """Curva de Gompertz, el modelo estandar de crecimiento en bovinos.

    W(t) = A * exp(-b * exp(-k*t)), con A el peso adulto y W(0) el peso al nacer.
    """
    age_days = max((when - animal.birth).total_seconds() / 86400.0, 1.0)
    asymptote = animal.mature_kg
    b = math.log(asymptote / BIRTH_WEIGHT_KG)
    k = 0.0030 * animal.vigor
    weight = asymptote * math.exp(-b * math.exp(-k * age_days))

    # Estacionalidad: en estiaje el hato baja de condicion corporal.
    season = math.sin((when.timetuple().tm_yday / 365.0) * 2 * math.pi)
    return weight * (1.0 + 0.025 * season)


def quantize(weight: float, rng: random.Random) -> float:
    """Ruido de bascula mas redondeo a la division real del indicador."""
    noisy = weight + rng.gauss(0.0, 1.2)
    return round(round(noisy / SCALE_DIVISION_KG) * SCALE_DIVISION_KG, 1)


def generate_events(
    *,
    rng: random.Random,
    herd: list[Animal],
    devices: list[str],
    days: int,
    interval_days: int,
    now: datetime,
) -> list[dict]:
    """Jornadas de pesaje cada `interval_days`; no todo el hato pasa por la manga."""
    events: list[dict] = []
    for offset in range(days, -1, -interval_days):
        session_day = now - timedelta(days=offset)
        device = rng.choice(devices)
        # 60-95% del hato por jornada: siempre queda ganado sin arrear.
        present = rng.sample(herd, k=max(int(len(herd) * rng.uniform(0.6, 0.95)), 1))
        for animal in present:
            if animal.birth > session_day:
                continue  # todavia no nacia
            captured_at = session_day.replace(
                hour=rng.randrange(7, 18),
                minute=rng.randrange(0, 60),
                second=rng.randrange(0, 60),
                microsecond=0,
            )
            if captured_at > now:
                # La jornada de hoy todavia no termina: un pesaje con fecha
                # futura es dato invalido, no dato faltante.
                continue
            iso = captured_at.isoformat()
            events.append(
                {
                    "event_id": str(uuid.uuid5(EVENT_NAMESPACE, f"{device}|{animal.tag_id}|{iso}")),
                    "device_id": device,
                    "tag_id": animal.tag_id,
                    "weight_kg": quantize(weight_at(animal, captured_at), rng),
                    "captured_at": iso,
                    # 3% inestable: el animal se movio y el indicador no fijo peso.
                    "stable": rng.random() > 0.03,
                    "source": "synthetic",
                }
            )
    events.sort(key=lambda event: event["captured_at"])
    return events


def post_batch(api: str, batch: list[dict], timeout: float) -> dict:
    payload = json.dumps({"readings": batch}).encode("utf-8")
    request = urllib.request.Request(
        f"{api.rstrip('/')}/v1/readings",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.load(response)


def push(api: str, events: list[dict], batch_size: int, timeout: float) -> tuple[int, int]:
    accepted = 0
    duplicates = 0
    total_batches = (len(events) + batch_size - 1) // batch_size
    for index, start in enumerate(range(0, len(events), batch_size), start=1):
        batch = events[start : start + batch_size]
        try:
            data = post_batch(api, batch, timeout)
        except (urllib.error.URLError, OSError) as exc:
            # Falla ruidosa: mejor abortar que dejar la base a medio sembrar.
            print(f"error enviando lote {index}: {exc}", file=sys.stderr)
            raise SystemExit(1) from exc
        accepted += len(data.get("accepted_ids", []))
        duplicates += len(data.get("duplicate_ids", []))
        print(f"  lote {index}/{total_batches}: {len(batch)} eventos", flush=True)
    return accepted, duplicates


def dump(path: str, herd: list[Animal], events: list[dict]) -> None:
    payload = {
        "herd": [
            {
                "tag_id": animal.tag_id,
                "breed": animal.breed,
                "sex": animal.sex,
                "birth": animal.birth.isoformat(),
                "mature_kg": round(animal.mature_kg, 1),
            }
            for animal in herd
        ],
        "readings": events,
    }
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=False)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Genera un hato sintetico y sus pesajes.")
    parser.add_argument("--api", help="URL de la API, p.ej. http://127.0.0.1:8000")
    parser.add_argument("--out", help="Escribir los eventos como JSON en vez de enviarlos")
    parser.add_argument("--animals", type=int, default=40, help="Tamano del hato")
    parser.add_argument("--days", type=int, default=90, help="Historia hacia atras, en dias")
    parser.add_argument("--interval-days", type=int, default=7, help="Dias entre jornadas")
    parser.add_argument("--devices", type=int, default=2, help="Estaciones que reportan")
    parser.add_argument(
        "--device-ids",
        help="IDs concretos separados por coma. Gana sobre --devices. "
        "Sirve para sembrar el hato de una organizacion ya creada.",
    )
    parser.add_argument("--batch-size", type=int, default=200)
    parser.add_argument("--timeout", type=float, default=30.0)
    parser.add_argument("--country-code", type=int, default=DEFAULT_COUNTRY_CODE)
    parser.add_argument("--seed", type=int, default=1234, help="Semilla determinista")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if not args.api and not args.out:
        print("Falta --api o --out", file=sys.stderr)
        return 2
    if args.interval_days < 1:
        print("--interval-days debe ser >= 1", file=sys.stderr)
        return 2

    rng = random.Random(args.seed)
    now = datetime.now(timezone.utc).replace(microsecond=0)
    herd = build_herd(rng, args.animals, args.country_code, now)
    if args.device_ids:
        devices = [d.strip() for d in args.device_ids.split(",") if d.strip()]
        if not devices:
            print("--device-ids no contiene ningun id", file=sys.stderr)
            return 2
    else:
        devices = [f"rpi-synthetic-{i + 1:03d}" for i in range(max(args.devices, 1))]
    events = generate_events(
        rng=rng,
        herd=herd,
        devices=devices,
        days=args.days,
        interval_days=args.interval_days,
        now=now,
    )

    print(
        f"hato={len(herd)} animales  estaciones={len(devices)}  "
        f"eventos={len(events)}  ventana={args.days}d  semilla={args.seed}"
    )

    if args.out:
        dump(args.out, herd, events)
        print(f"escrito {args.out}")

    if args.api:
        accepted, duplicates = push(args.api, events, args.batch_size, args.timeout)
        print(f"aceptados={accepted} duplicados={duplicates}")
        if duplicates:
            print("(duplicados esperados si ya corriste esta misma semilla)")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
