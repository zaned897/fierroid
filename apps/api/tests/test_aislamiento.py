"""Aislamiento entre organizaciones.

Es la prueba mas importante del repo. Todo lo demas puede fallar y se arregla;
que un rancho vea los pesajes de otro es el fallo que no se puede deshacer,
porque el dato ya se filtro.
"""

from __future__ import annotations

import os
import uuid
from datetime import datetime, timedelta, timezone

import pytest

DSN = os.getenv("FIERRO_TEST_PG_DSN", "").strip()

pytestmark = pytest.mark.skipif(not DSN, reason="FIERRO_TEST_PG_DSN no definido")

SUFIJO = uuid.uuid4().hex[:8]
DEVICE_A = f"rpi-aisl-a-{SUFIJO}"
DEVICE_B = f"rpi-aisl-b-{SUFIJO}"
DEVICE_HUERFANA = f"rpi-aisl-sin-{SUFIJO}"


@pytest.fixture(scope="module")
def mundo():
    """Dos organizaciones con una estacion cada una, mas una sin asignar."""
    import psycopg
    from fierro_api.auth import create_user
    from fierro_api.migrate import apply_migrations
    from fierro_api.tenancy import build_specs, seed_tenants

    apply_migrations(DSN)
    seed_tenants(DSN, build_specs(orgs=2, ranches_per_org=1, devices_per_ranch=1))

    correo_a = f"ana-{SUFIJO}@fierro.test"
    correo_b = f"beto-{SUFIJO}@fierro.test"
    correo_su = f"admin-{SUFIJO}@fierro.test"
    create_user(DSN, email=correo_a, password="clave-de-prueba", org_slug="los-encinos")
    create_user(DSN, email=correo_b, password="clave-de-prueba", org_slug="valle-verde")
    create_user(DSN, email=correo_su, password="clave-de-prueba", is_superuser=True)

    ahora = datetime.now(timezone.utc)
    with psycopg.connect(DSN) as conn, conn.cursor() as cur:
        for device, org, rancho in (
            (DEVICE_A, "los-encinos", "san-jose"),
            (DEVICE_B, "valle-verde", "la-mesa"),
        ):
            cur.execute(
                """
                INSERT INTO devices (device_id, pending_count, last_seen, ranch_id)
                VALUES (%s, 0, now(), (
                    SELECT r.id FROM ranches r
                    JOIN organizations o ON o.id = r.org_id
                    WHERE o.slug = %s AND r.slug = %s
                ))
                ON CONFLICT (device_id) DO NOTHING
                """,
                (device, org, rancho),
            )
        cur.execute(
            "INSERT INTO devices (device_id, pending_count, last_seen) "
            "VALUES (%s, 0, now()) ON CONFLICT (device_id) DO NOTHING",
            (DEVICE_HUERFANA,),
        )

        for device in (DEVICE_A, DEVICE_B, DEVICE_HUERFANA):
            for n in range(3):
                cur.execute(
                    """
                    INSERT INTO readings
                      (event_id, device_id, tag_id, weight_kg, captured_at, stable, source)
                    VALUES (%s, %s, %s, %s, %s, true, 'test')
                    ON CONFLICT (event_id) DO NOTHING
                    """,
                    (
                        f"evt-{device}-{n}",
                        device,
                        f"48400000000{n}{device[-4:]}"[:15],
                        400.0 + n,
                        ahora - timedelta(minutes=n),
                    ),
                )
        conn.commit()

    yield {"a": correo_a, "b": correo_b, "su": correo_su}

    with psycopg.connect(DSN) as conn, conn.cursor() as cur:
        cur.execute(
            "DELETE FROM readings WHERE device_id = ANY(%s)",
            ([DEVICE_A, DEVICE_B, DEVICE_HUERFANA],),
        )
        cur.execute(
            "DELETE FROM devices WHERE device_id = ANY(%s)",
            ([DEVICE_A, DEVICE_B, DEVICE_HUERFANA],),
        )
        cur.execute(
            "DELETE FROM users WHERE email = ANY(%s)", ([correo_a, correo_b, correo_su],)
        )
        conn.commit()


@pytest.fixture
def client(monkeypatch):
    from dataclasses import replace

    from fastapi.testclient import TestClient
    from fierro_api import main as main_module
    from fierro_api.store_pg import PostgresReadingStore

    # No basta con parchear settings: `store` es un singleton creado al importar
    # el modulo, asi que sin esto el login iria a Postgres y las lecturas a
    # SQLite vacio.
    monkeypatch.setattr(main_module, "settings", replace(main_module.settings, dsn=DSN))
    monkeypatch.setattr(main_module, "store", PostgresReadingStore(DSN))
    return TestClient(main_module.app)


def entrar(client, correo: str) -> dict[str, str]:
    resp = client.post(
        "/v1/auth/login", json={"email": correo, "password": "clave-de-prueba"}
    )
    assert resp.status_code == 200, resp.text
    return {"Authorization": f"Bearer {resp.json()['api_key']}"}


def devices_visibles(client, cabeceras) -> set[str]:
    resp = client.get("/v1/devices", headers=cabeceras)
    assert resp.status_code == 200
    return {d["device_id"] for d in resp.json()["devices"]}


def devices_en_lecturas(client, cabeceras) -> set[str]:
    resp = client.get("/v1/readings?limit=200", headers=cabeceras)
    assert resp.status_code == 200
    return {r["device_id"] for r in resp.json()["readings"]}


def test_una_organizacion_no_ve_las_estaciones_de_otra(client, mundo):
    a = entrar(client, mundo["a"])
    b = entrar(client, mundo["b"])

    vistos_a = devices_visibles(client, a)
    vistos_b = devices_visibles(client, b)

    assert DEVICE_A in vistos_a
    assert DEVICE_B not in vistos_a
    assert DEVICE_B in vistos_b
    assert DEVICE_A not in vistos_b


def test_una_organizacion_no_ve_las_lecturas_de_otra(client, mundo):
    a = entrar(client, mundo["a"])
    b = entrar(client, mundo["b"])

    assert DEVICE_B not in devices_en_lecturas(client, a)
    assert DEVICE_A not in devices_en_lecturas(client, b)


def test_el_superusuario_ve_ambas(client, mundo):
    su = entrar(client, mundo["su"])
    vistos = devices_visibles(client, su)

    assert {DEVICE_A, DEVICE_B} <= vistos


def test_una_estacion_sin_asignar_no_cuelga_de_nadie(client, mundo):
    """Sus lecturas se guardan, pero no se le muestran a un inquilino ajeno."""
    a = entrar(client, mundo["a"])
    su = entrar(client, mundo["su"])

    assert DEVICE_HUERFANA not in devices_visibles(client, a)
    assert DEVICE_HUERFANA not in devices_en_lecturas(client, a)
    # El superusuario si la ve: alguien tiene que poder asignarla.
    assert DEVICE_HUERFANA in devices_visibles(client, su)


def test_filtrar_por_estacion_ajena_no_la_expone(client, mundo):
    """El filtro no puede usarse para saltarse el alcance."""
    a = entrar(client, mundo["a"])

    resp = client.get(f"/v1/readings?device_id={DEVICE_B}", headers=a)
    assert resp.status_code == 200
    assert resp.json()["readings"] == []


def test_paginacion_no_se_salta_ni_repite(client, mundo):
    su = entrar(client, mundo["su"])

    primera = client.get("/v1/readings?limit=5", headers=su).json()
    assert primera["next_cursor"]

    segunda = client.get(
        f"/v1/readings?limit=5&cursor={primera['next_cursor']}", headers=su
    ).json()

    ids_1 = [r["event_id"] for r in primera["readings"]]
    ids_2 = [r["event_id"] for r in segunda["readings"]]

    assert len(ids_1) == 5
    assert not set(ids_1) & set(ids_2), "una lectura salio en dos paginas"


def test_la_paginacion_respeta_el_alcance(client, mundo):
    """Recorrer todas las paginas no debe destapar otra organizacion."""
    a = entrar(client, mundo["a"])

    cursor = None
    vistos: set[str] = set()
    for _ in range(20):  # tope de seguridad para no ciclar
        url = "/v1/readings?limit=50" + (f"&cursor={cursor}" if cursor else "")
        body = client.get(url, headers=a).json()
        vistos |= {r["device_id"] for r in body["readings"]}
        cursor = body["next_cursor"]
        if not cursor:
            break

    assert DEVICE_B not in vistos
    assert DEVICE_HUERFANA not in vistos


def test_cursor_manipulado_da_400(client, mundo):
    a = entrar(client, mundo["a"])
    resp = client.get("/v1/readings?cursor=no-es-base64-valido!!", headers=a)
    assert resp.status_code == 400


def test_ultima_pagina_no_ofrece_cursor(client, mundo):
    a = entrar(client, mundo["a"])
    body = client.get("/v1/readings?limit=200", headers=a).json()

    # Menos filas que el limite significa que ya no hay mas.
    if len(body["readings"]) < 200:
        assert body["next_cursor"] is None
