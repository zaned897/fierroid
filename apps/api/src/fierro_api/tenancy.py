"""Organizaciones, ranchos y asignacion de estaciones.

Sembrar la estructura multi-cliente es una operacion administrativa, no publica:
va directo a la base y no expone endpoints. Las lecturas siguen entrando por
`POST /v1/readings`, que es el camino real y ejercita la idempotencia.

Solo Postgres. El modo SQLite es de laboratorio y es de un solo inquilino.
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from typing import Any

from fierro_api.db import require_row

# Nombres verosimiles de ganaderia mexicana, para que los datos de prueba se
# lean como datos y no como "org-1", "org-2".
ORG_CATALOG: list[tuple[str, str, list[str]]] = [
    ("los-encinos", "Ganadera Los Encinos", ["san-jose", "el-mezquite"]),
    ("valle-verde", "Rancho Valle Verde", ["la-mesa", "los-sauces"]),
    ("santa-rita", "Agropecuaria Santa Rita", ["el-carrizo", "las-palmas"]),
    ("el-porvenir", "Ganadera El Porvenir", ["la-loma", "el-vado"]),
    ("dos-rios", "Rancho Dos Rios", ["el-salto", "la-vega"]),
]


@dataclass(frozen=True)
class RanchSpec:
    slug: str
    name: str
    devices: list[str]


@dataclass(frozen=True)
class OrgSpec:
    slug: str
    name: str
    ranches: list[RanchSpec]

    @property
    def device_ids(self) -> list[str]:
        return [d for r in self.ranches for d in r.devices]

    @property
    def seed(self) -> int:
        """Semilla derivada del slug: cada organizacion recibe un hato distinto.

        Suma de ordinales y no hash(): hash() de str varia entre procesos por
        PYTHONHASHSEED, y aqui el punto es que sea reproducible.
        """
        return sum(map(ord, self.slug))


def build_specs(*, orgs: int, ranches_per_org: int, devices_per_ranch: int) -> list[OrgSpec]:
    if orgs > len(ORG_CATALOG):
        raise ValueError(f"maximo {len(ORG_CATALOG)} organizaciones en el catalogo")

    specs: list[OrgSpec] = []
    for org_slug, org_name, ranch_slugs in ORG_CATALOG[:orgs]:
        if ranches_per_org > len(ranch_slugs):
            raise ValueError(f"maximo {len(ranch_slugs)} ranchos para {org_slug}")
        ranches = []
        for index, ranch_slug in enumerate(ranch_slugs[:ranches_per_org]):
            devices = [
                f"rpi-{org_slug}-{index * devices_per_ranch + n + 1:03d}"
                for n in range(devices_per_ranch)
            ]
            ranches.append(
                RanchSpec(
                    slug=ranch_slug,
                    name=ranch_slug.replace("-", " ").title(),
                    devices=devices,
                )
            )
        specs.append(OrgSpec(slug=org_slug, name=org_name, ranches=ranches))
    return specs


def seed_tenants(dsn: str, specs: list[OrgSpec]) -> list[dict[str, Any]]:
    """Crea organizaciones, ranchos y estaciones. Idempotente por slug."""
    import psycopg

    resumen: list[dict[str, Any]] = []
    with psycopg.connect(dsn) as conn, conn.cursor() as cur:
        for org in specs:
            cur.execute(
                """
                INSERT INTO organizations (slug, name) VALUES (%s, %s)
                ON CONFLICT (slug) DO UPDATE SET name = EXCLUDED.name
                RETURNING id
                """,
                (org.slug, org.name),
            )
            org_id = require_row(cur.fetchone(), "crear organizacion")[0]

            ranchos = []
            for ranch in org.ranches:
                cur.execute(
                    """
                    INSERT INTO ranches (org_id, slug, name) VALUES (%s, %s, %s)
                    ON CONFLICT (org_id, slug) DO UPDATE SET name = EXCLUDED.name
                    RETURNING id
                    """,
                    (org_id, ranch.slug, ranch.name),
                )
                ranch_id = require_row(cur.fetchone(), "crear rancho")[0]

                for device_id in ranch.devices:
                    # Re-sembrar reasigna: es una herramienta de desarrollo y
                    # debe converger al estado descrito, no acumular.
                    cur.execute(
                        """
                        INSERT INTO devices (device_id, pending_count, last_seen, ranch_id)
                        VALUES (%s, 0, now(), %s)
                        ON CONFLICT (device_id) DO UPDATE SET ranch_id = EXCLUDED.ranch_id
                        """,
                        (device_id, ranch_id),
                    )
                ranchos.append({"slug": ranch.slug, "devices": list(ranch.devices)})

            resumen.append({"org": org.slug, "name": org.name, "ranches": ranchos})
        conn.commit()
    return resumen


def list_tenants(dsn: str) -> list[dict[str, Any]]:
    """Arbol organizacion -> ranchos -> estaciones, con conteo de lecturas."""
    import psycopg
    from psycopg.rows import dict_row

    with psycopg.connect(dsn, row_factory=dict_row) as conn, conn.cursor() as cur:
        cur.execute(
            """
            SELECT o.slug AS org, o.name AS org_name,
                   r.slug AS ranch, d.device_id,
                   (SELECT count(*) FROM readings x WHERE x.device_id = d.device_id) AS readings
            FROM organizations o
            LEFT JOIN ranches r ON r.org_id = o.id
            LEFT JOIN devices d ON d.ranch_id = r.id
            ORDER BY o.slug, r.slug, d.device_id
            """
        )
        return [dict(row) for row in cur.fetchall()]


def unassigned_devices(dsn: str) -> list[str]:
    """Estaciones que reportaron sin estar asignadas a ningun rancho."""
    import psycopg

    with psycopg.connect(dsn) as conn, conn.cursor() as cur:
        cur.execute("SELECT device_id FROM devices WHERE ranch_id IS NULL ORDER BY device_id")
        return [row[0] for row in cur.fetchall()]


def main(argv: list[str] | None = None) -> int:
    from fierro_api.settings import Settings

    parser = argparse.ArgumentParser(description="Siembra organizaciones, ranchos y estaciones.")
    parser.add_argument("--orgs", type=int, default=3)
    parser.add_argument("--ranches-per-org", type=int, default=1)
    parser.add_argument("--devices-per-ranch", type=int, default=2)
    parser.add_argument("--list", action="store_true", help="Solo mostrar lo que ya existe")
    args = parser.parse_args(argv)

    dsn = Settings.from_env().dsn
    if not dsn:
        print(
            "FIERRO_API_DSN no esta definido. La siembra de inquilinos requiere Postgres.\n"
            "  FIERRO_API_DSN=postgresql://fierro:fierro@localhost:5432/fierro",
            file=sys.stderr,
        )
        return 2

    if args.list:
        for row in list_tenants(dsn):
            print(f"  {row['org']:<14} {row['ranch'] or '-':<12} "
                  f"{row['device_id'] or '(sin estaciones)':<26} {row['readings']} lecturas")
        huerfanas = unassigned_devices(dsn)
        if huerfanas:
            print(f"\n  sin asignar: {', '.join(huerfanas)}")
        return 0

    specs = build_specs(
        orgs=args.orgs,
        ranches_per_org=args.ranches_per_org,
        devices_per_ranch=args.devices_per_ranch,
    )
    seed_tenants(dsn, specs)

    print(f"sembradas {len(specs)} organizaciones\n")
    for org in specs:
        ranchos = ", ".join(r.slug for r in org.ranches)
        print(f"  {org.name}  ({org.slug})")
        print(f"    ranchos:     {ranchos}")
        print(f"    estaciones:  {', '.join(org.device_ids)}")
        print(
            f"    poblar:      python3 scripts/seed_synthetic.py --api http://127.0.0.1:8000 "
            f"--device-ids {','.join(org.device_ids)} --seed {org.seed} --animals 40 --days 120"
        )
        print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
