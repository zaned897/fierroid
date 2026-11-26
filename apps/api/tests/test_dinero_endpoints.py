"""Endpoints de cuentas (#174) sobre Postgres: lo que verá la ficha y el hato."""
import os
from dataclasses import replace
from datetime import date
from uuid import uuid4

import pytest

DSN = os.getenv("FIERRO_TEST_PG_DSN", "")
pytestmark = pytest.mark.skipif(not DSN, reason="FIERRO_TEST_PG_DSN no definido")
HOY = date(2026, 11, 5)


@pytest.fixture
def world(monkeypatch):
    import psycopg
    from fastapi.testclient import TestClient
    from fierro_api import main
    from fierro_api.auth import AuthUser, create_user
    from fierro_api.migrate import apply_migrations
    from fierro_api.store import build_store
    from fierro_api.tenancy import build_specs, seed_tenants

    apply_migrations(DSN)
    seed_tenants(DSN, build_specs(orgs=2, ranches_per_org=1, devices_per_ranch=1))
    prefix = "cuentas" + uuid4().hex[:8]
    emails = [f"{prefix}-{i}@example.test" for i in range(2)]
    for email, org in zip(emails, ["los-encinos", "valle-verde"], strict=True):
        create_user(DSN, email=email, org_slug=org)
    with psycopg.connect(DSN) as conn, conn.cursor() as cur:
        cur.execute("SELECT u.id,u.email,u.org_id,o.slug FROM users u JOIN organizations o "
                    "ON o.id=u.org_id WHERE u.email=ANY(%s) ORDER BY u.email", (emails,))
        users = [AuthUser(*row, False) for row in cur.fetchall()]
        for suffix in ("a", "b"):
            cur.execute("INSERT INTO animals(org_id,tag_id) VALUES (%s,%s)",
                        (users[0].org_id, prefix + suffix))
        cur.execute("SELECT d.device_id FROM devices d JOIN ranches r ON r.id=d.ranch_id "
                    "WHERE r.org_id=%s ORDER BY d.device_id LIMIT 1", (users[0].org_id,))
        device = cur.fetchone()[0]
    store = build_store(dsn=DSN, db_path="")
    monkeypatch.setattr(main, "settings", replace(main.settings, dsn=DSN))
    monkeypatch.setattr(main, "store", store)
    monkeypatch.setattr(main, "_hoy", lambda: HOY)
    # Página de 1: las cuentas deben leer todas las lecturas, no la primera página.
    monkeypatch.setattr(main, "PAGINA_CUENTAS", 1)
    main.app.dependency_overrides[main.current_user] = lambda: users[0]
    with TestClient(main.app) as client:
        yield client, users, prefix, device, store, main
    main.app.dependency_overrides.pop(main.current_user, None)
    store.close()
    with psycopg.connect(DSN) as conn, conn.cursor() as cur:
        cur.execute("DELETE FROM money_movements WHERE author_id=ANY(%s)", ([u.id for u in users],))
        cur.execute("DELETE FROM readings WHERE event_id LIKE %s", (prefix + "%",))
        cur.execute("DELETE FROM animals WHERE tag_id LIKE %s", (prefix + "%",))
        cur.execute("DELETE FROM users WHERE email=ANY(%s)", (emails,))


def post(client, **data):
    body = {"movement_id": str(uuid4()), "scope": "hato", "animals": [], **data}
    response = client.post("/v1/dinero/movimientos", json=body)
    assert response.status_code == 200, response.text
    return response.json()["movement_id"]


def weigh(store, prefix, device, tag, day, kg):
    store.upsert_readings([{
        "event_id": f"{prefix}-{tag}-{day}", "device_id": device, "tag_id": tag,
        "weight_kg": kg, "captured_at": f"{day}T08:00:00+00:00", "stable": True,
        "source": "serial",
    }])


def seed(client, prefix, device, store, *, price=True):
    a = prefix + "a"
    post(client, kind="compra", scope="animales", animals=[a], amount_mxn="10000",
         occurred_on="2026-10-01")
    post(client, kind="gasto", category="alimento", amount_mxn="3000",
         occurred_on="2026-10-30", period_start="2026-10-01", period_end="2026-10-30")
    if price:
        post(client, kind="precio_mercado", precio_kg_mxn="45", occurred_on="2026-10-01")
    weigh(store, prefix, device, a, "2026-10-10", 400)
    weigh(store, prefix, device, a, "2026-10-20", 411)
    return a


def test_vaca_con_dinero_calculado(world):
    client, _, prefix, device, store, _ = world
    a = seed(client, prefix, device, store)
    body = client.get(f"/v1/animals/{a}/dinero", params={"dia": "2026-10-20"}).json()
    # Alimento entre dos vacas: 50 MXN por vaca por día, 20 días corridos.
    assert body["costo_acumulado"]["mxn"] == "11000.00"
    assert body["costo_acumulado"]["por_categoria"] == {"alimento": "1000.00",
                                                        "compra": "10000.00"}
    assert body["valor_hoy"]["mxn"] == "18495.00"
    assert body["resultado"]["mxn"] == "7495.00"
    # 1.1 kg/día × 45 − 50 de costo del día.
    assert body["ganancia_dia_mxn"]["mxn"] == "-0.50"
    assert body["ganancia_dia_mxn"]["kg_dia"] == "1.100"
    assert body["valor_hoy"]["fuente"]["pesaje"]["event_id"] == f"{prefix}-{a}-2026-10-20"


def test_vaca_sin_precio_muestra_costos_y_motivo(world):
    client, _, prefix, device, store, _ = world
    a = seed(client, prefix, device, store, price=False)
    body = client.get(f"/v1/animals/{a}/dinero").json()
    assert body["costo_acumulado"]["mxn"] == "11500.00"
    for cifra in ("valor_hoy", "resultado", "ganancia_dia_mxn"):
        assert body[cifra] == {"mxn": None, "motivo": "falta_precio", "fuente": {}}


def test_hato_del_mes_y_aislamiento(world):
    client, users, prefix, device, store, main = world
    a = seed(client, prefix, device, store)
    body = client.get("/v1/hato/dinero", params={"mes": "2026-10"}).json()
    assert body["dia"] == "2026-10-31"
    assert body["mes"]["por_categoria"] == {"alimento": "3000.00"}
    assert body["mes"]["compras_mxn"] == "10000.00"
    mios = {x["tag_id"]: x for x in body["animales"] if x["tag_id"].startswith(prefix)}
    assert set(mios) == {a, prefix + "b"}
    assert mios[a]["costo_acumulado"]["mxn"] == "11500.00"
    assert client.get("/v1/hato/dinero", params={"mes": "2026-12"}).status_code == 422
    assert client.get("/v1/hato/dinero", params={"mes": "2026-13"}).status_code == 422

    main.app.dependency_overrides[main.current_user] = lambda: users[1]
    assert client.get(f"/v1/animals/{a}/dinero").status_code == 404
    otro = client.get("/v1/hato/dinero", params={"mes": "2026-10"}).json()
    assert otro["mes"]["gastos_mxn"] == "0.00"
    assert not [x for x in otro["animales"] if x["tag_id"].startswith(prefix)]
