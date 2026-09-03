"""Organizaciones, ranchos y asignacion de estaciones.

Las pruebas de catalogo corren siempre; las de base requieren
FIERRO_TEST_PG_DSN, igual que las del store Postgres.
"""

from __future__ import annotations

import os
import uuid

import pytest
from fierro_api.tenancy import build_specs

DSN = os.getenv("FIERRO_TEST_PG_DSN", "").strip()


# --------------------------------------------------------------------------
# Catalogo: sin base de datos
# --------------------------------------------------------------------------


def test_cada_organizacion_recibe_semilla_distinta():
    """Si dos organizaciones comparten semilla, sus hatos salen identicos."""
    specs = build_specs(orgs=5, ranches_per_org=1, devices_per_ranch=2)
    semillas = [s.seed for s in specs]
    assert len(set(semillas)) == len(semillas)


def test_semilla_es_reproducible_entre_procesos():
    """Deriva de ordinales, no de hash(), que cambia con PYTHONHASHSEED."""
    a = build_specs(orgs=3, ranches_per_org=1, devices_per_ranch=1)
    b = build_specs(orgs=3, ranches_per_org=1, devices_per_ranch=1)
    assert [s.seed for s in a] == [s.seed for s in b]


def test_ids_de_estacion_no_se_repiten_entre_organizaciones():
    specs = build_specs(orgs=5, ranches_per_org=2, devices_per_ranch=2)
    todos = [d for s in specs for d in s.device_ids]
    assert len(todos) == len(set(todos))


def test_estructura_pedida_es_la_construida():
    specs = build_specs(orgs=2, ranches_per_org=2, devices_per_ranch=3)
    assert len(specs) == 2
    for spec in specs:
        assert len(spec.ranches) == 2
        assert all(len(r.devices) == 3 for r in spec.ranches)
        assert len(spec.device_ids) == 6


def test_pedir_mas_organizaciones_que_el_catalogo_falla():
    """Falla ruidosa en vez de inventar nombres genericos."""
    with pytest.raises(ValueError, match="catalogo"):
        build_specs(orgs=99, ranches_per_org=1, devices_per_ranch=1)


def test_pedir_mas_ranchos_de_los_definidos_falla():
    with pytest.raises(ValueError, match="ranchos"):
        build_specs(orgs=1, ranches_per_org=99, devices_per_ranch=1)


# --------------------------------------------------------------------------
# Base de datos
# --------------------------------------------------------------------------

pg = pytest.mark.skipif(not DSN, reason="FIERRO_TEST_PG_DSN no definido")


@pytest.fixture(scope="module")
def migrated():
    from fierro_api.migrate import apply_migrations

    apply_migrations(DSN)
    return DSN


@pytest.fixture
def conn(migrated):
    import psycopg

    with psycopg.connect(migrated) as connection:
        yield connection


@pg
def test_migracion_crea_las_tablas(conn):
    with conn.cursor() as cur:
        cur.execute(
            "SELECT table_name FROM information_schema.tables "
            "WHERE table_schema = 'public' AND table_name IN ('organizations', 'ranches')"
        )
        assert {row[0] for row in cur.fetchall()} == {"organizations", "ranches"}


@pg
def test_backfill_asigna_las_estaciones_previas_a_demo(conn):
    """Nada queda huerfano tras migrar: lo que existia cae en la org demo."""
    with conn.cursor() as cur:
        cur.execute("SELECT slug FROM organizations WHERE slug = 'demo'")
        assert cur.fetchone() is not None


@pg
def test_sembrar_dos_veces_no_duplica(migrated):
    from fierro_api.tenancy import list_tenants, seed_tenants

    specs = build_specs(orgs=3, ranches_per_org=1, devices_per_ranch=2)
    seed_tenants(migrated, specs)
    primera = list_tenants(migrated)
    seed_tenants(migrated, specs)
    segunda = list_tenants(migrated)

    assert primera == segunda


@pg
def test_cada_organizacion_ve_solo_sus_estaciones(migrated):
    from fierro_api.tenancy import list_tenants, seed_tenants

    specs = build_specs(orgs=3, ranches_per_org=1, devices_per_ranch=2)
    seed_tenants(migrated, specs)

    por_org: dict[str, set[str]] = {}
    for row in list_tenants(migrated):
        if row["device_id"]:
            por_org.setdefault(row["org"], set()).add(row["device_id"])

    for spec in specs:
        assert por_org[spec.slug] == set(spec.device_ids)

    # Ninguna estacion aparece bajo dos organizaciones.
    vistos: set[str] = set()
    for devices in por_org.values():
        assert not (vistos & devices)
        vistos |= devices


@pg
def test_estacion_desconocida_queda_sin_asignar_y_no_se_pierde(conn, migrated):
    """Una estacion nueva puede reportar antes de que alguien la asigne."""
    from fierro_api.tenancy import unassigned_devices

    device_id = f"rpi-nueva-{uuid.uuid4().hex[:8]}"
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO devices (device_id, pending_count, last_seen) VALUES (%s, 0, now())",
            (device_id,),
        )
        conn.commit()

    try:
        assert device_id in unassigned_devices(migrated)
    finally:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM devices WHERE device_id = %s", (device_id,))
            conn.commit()


@pg
def test_borrar_un_rancho_desasigna_pero_no_borra_la_estacion(conn):
    """ON DELETE SET NULL: jamas se borran filas de estacion en cascada."""
    device_id = f"rpi-tmp-{uuid.uuid4().hex[:8]}"
    slug = f"tmp-{uuid.uuid4().hex[:8]}"
    with conn.cursor() as cur:
        cur.execute("SELECT id FROM organizations WHERE slug = 'demo'")
        org_id = cur.fetchone()[0]
        cur.execute(
            "INSERT INTO ranches (org_id, slug, name) VALUES (%s, %s, %s) RETURNING id",
            (org_id, slug, "Temporal"),
        )
        ranch_id = cur.fetchone()[0]
        cur.execute(
            "INSERT INTO devices (device_id, pending_count, last_seen, ranch_id) "
            "VALUES (%s, 0, now(), %s)",
            (device_id, ranch_id),
        )
        conn.commit()

        cur.execute("DELETE FROM ranches WHERE id = %s", (ranch_id,))
        conn.commit()

        cur.execute("SELECT ranch_id FROM devices WHERE device_id = %s", (device_id,))
        fila = cur.fetchone()
        assert fila is not None, "la estacion se borro en cascada"
        assert fila[0] is None

        cur.execute("DELETE FROM devices WHERE device_id = %s", (device_id,))
        conn.commit()


@pg
def test_no_se_puede_borrar_una_organizacion_con_ranchos(conn):
    """RESTRICT: borrar una organizacion poblada debe doler, no ser silencioso."""
    import psycopg

    with conn.cursor() as cur:
        cur.execute("SELECT id FROM organizations WHERE slug = 'demo'")
        org_id = cur.fetchone()[0]
        with pytest.raises(psycopg.errors.ForeignKeyViolation):
            cur.execute("DELETE FROM organizations WHERE id = %s", (org_id,))
    conn.rollback()
