"""Rancho demo por cuenta (016): acceso y purga.

Lo que no puede pasar: que el usuario de una cuenta abra el demo de otra, o
que una purga borre algo que no sea de demo.
"""

from __future__ import annotations

import os
import uuid
from datetime import UTC, datetime

import pytest

DSN = os.getenv("FIERRO_TEST_PG_DSN", "").strip()

pytestmark = pytest.mark.skipif(not DSN, reason="FIERRO_TEST_PG_DSN no definido")

SUFIJO = uuid.uuid4().hex[:8]
ORG_A = f"demo-a-{SUFIJO}"
ORG_B = f"demo-b-{SUFIJO}"
CORREO_A = f"ana-demo-{SUFIJO}@fierro.test"
CORREO_B = f"beto-demo-{SUFIJO}@fierro.test"
CORREO_SU = f"admin-demo-{SUFIJO}@fierro.test"


@pytest.fixture(scope="module")
def mundo():
    from fierro_api.admin import crear_org
    from fierro_api.auth import create_user
    from fierro_api.migrate import apply_migrations

    apply_migrations(DSN)
    crear_org(DSN, slug=ORG_A, name="Rancho A")
    crear_org(DSN, slug=ORG_B, name="Rancho B")
    create_user(DSN, email=CORREO_A, password="clave-de-prueba", org_slug=ORG_A)
    create_user(DSN, email=CORREO_B, password="clave-de-prueba", org_slug=ORG_B)
    create_user(DSN, email=CORREO_SU, password="clave-de-prueba", is_superuser=True)
    yield


@pytest.fixture
def client(mundo, monkeypatch):
    from dataclasses import replace

    from fastapi.testclient import TestClient
    from fierro_api import main as main_module
    from fierro_api.store_pg import PostgresReadingStore

    store = PostgresReadingStore(DSN)
    monkeypatch.setattr(main_module, "settings", replace(main_module.settings, dsn=DSN))
    monkeypatch.setattr(main_module, "store", store)
    yield TestClient(main_module.app)
    store.close()


def entrar(client, correo: str) -> dict[str, str]:
    resp = client.post("/v1/auth/login", json={"email": correo, "password": "clave-de-prueba"})
    assert resp.status_code == 200, resp.text
    return {"Authorization": f"Bearer {resp.json()['api_key']}"}


def _sembrar_demo(client, su, org: str, fuente: str = "demo") -> str:
    resp = client.post(f"/v1/orgs/{org}/demo", headers=su)
    assert resp.status_code == 200, resp.text
    demo = resp.json()["slug"]
    device = f"{demo}-manga"
    assert client.post(f"/v1/orgs/{demo}/ranches", headers=su,
                       json={"slug": "corrales", "name": "Corrales"}).status_code in (201, 400)
    assert client.put(f"/v1/devices/{device}", headers=su,
                      json={"org": demo, "ranch": "corrales"}).status_code == 200
    tag = f"4840000{SUFIJO[:8]}"[:15]
    resp = client.post("/v1/readings", json={
        "event_id": str(uuid.uuid4()), "device_id": device, "tag_id": tag,
        "weight_kg": 312.5, "captured_at": datetime.now(UTC).isoformat(),
        "stable": True, "source": fuente,
    })
    assert resp.status_code == 200, resp.text
    resp = client.put(f"/v1/animals/{tag}?org={demo}", headers=su, json={"alias": "Canelo"})
    assert resp.status_code == 200, resp.text
    resp = client.post(f"/v1/dinero/movimientos?org={demo}", headers=su, json={
        "movement_id": str(uuid.uuid4()), "kind": "compra", "amount_mxn": "21000.00",
        "weight_kg": "300.00", "occurred_on": "2026-06-01", "scope": "animales",
        "animals": [tag],
    })
    assert resp.status_code == 200, resp.text
    compra = resp.json()["movement_id"]
    resp = client.post(f"/v1/dinero/movimientos/{compra}/anular?org={demo}", headers=su,
                       json={"movement_id": str(uuid.uuid4()), "occurred_on": "2026-06-02"})
    assert resp.status_code == 200, resp.text
    return demo


def test_demo_es_idempotente_y_aparece_en_me(client):
    su = entrar(client, CORREO_SU)
    primero = client.post(f"/v1/orgs/{ORG_A}/demo", headers=su).json()
    segundo = client.post(f"/v1/orgs/{ORG_A}/demo", headers=su).json()
    assert primero["slug"] == segundo["slug"] == f"{ORG_A}-demo"
    assert segundo["creado"] is False

    yo = client.get("/v1/auth/me", headers=entrar(client, CORREO_A)).json()
    assert yo["org"] == ORG_A and yo["demo_org"] == f"{ORG_A}-demo"
    assert client.get("/v1/auth/me", headers=entrar(client, CORREO_B)).json()["demo_org"] is None


def test_un_demo_no_lleva_demo_propio(client):
    su = entrar(client, CORREO_SU)
    client.post(f"/v1/orgs/{ORG_A}/demo", headers=su)
    resp = client.post(f"/v1/orgs/{ORG_A}-demo/demo", headers=su)
    assert resp.status_code == 400


def test_usuario_ve_su_demo_y_no_el_ajeno(client):
    su = entrar(client, CORREO_SU)
    demo_a = _sembrar_demo(client, su, ORG_A)
    a, b = entrar(client, CORREO_A), entrar(client, CORREO_B)

    propias = client.get("/v1/readings", headers=a).json()["readings"]
    demo = client.get(f"/v1/readings?org={demo_a}", headers=a).json()["readings"]
    assert all(r["source"] != "demo" for r in propias)
    assert demo and all(r["source"] == "demo" for r in demo)
    assert client.get(f"/v1/animals?org={demo_a}", headers=a).status_code == 200
    assert client.get(f"/v1/dinero/movimientos?org={demo_a}", headers=a).status_code == 200

    # Un `org` ajeno se ignora y queda en la cuenta propia, como en el resto de la API.
    ajenas = client.get(f"/v1/readings?org={demo_a}", headers=b).json()["readings"]
    assert all(r["source"] != "demo" for r in ajenas)
    assert client.get(f"/v1/animals?org={demo_a}", headers=b).json()["animals"] == []
    assert client.get(f"/v1/devices?org={demo_a}", headers=b).json()["devices"] == []
    assert client.get(f"/v1/dinero/movimientos?org={demo_a}", headers=b).json()["movements"] == []


def test_purga_borra_todo_el_demo_y_nada_mas(client):
    su = entrar(client, CORREO_SU)
    demo = _sembrar_demo(client, su, ORG_B)

    resp = client.delete(f"/v1/orgs/{ORG_B}/demo", headers=su)
    assert resp.status_code == 200, resp.text
    borrado = resp.json()["borrado"]
    assert borrado["organizations"] == 1
    assert borrado["money_movements"] == 2  # compra + su anulacion
    assert borrado["readings"] == 1

    orgs = {o["slug"] for o in client.get("/v1/orgs", headers=su).json()["orgs"]}
    assert ORG_B in orgs and demo not in orgs
    assert client.get("/v1/auth/me", headers=entrar(client, CORREO_B)).json()["demo_org"] is None
    assert client.delete(f"/v1/orgs/{ORG_B}/demo", headers=su).status_code == 400


def test_purga_se_niega_con_pesajes_reales(client):
    org = f"demo-c-{SUFIJO}"
    from fierro_api.admin import crear_org

    crear_org(DSN, slug=org, name="Rancho C")
    su = entrar(client, CORREO_SU)
    _sembrar_demo(client, su, org, fuente="serial")

    resp = client.delete(f"/v1/orgs/{org}/demo", headers=su)
    assert resp.status_code == 400
    assert "no son de demo" in resp.json()["detail"]


def test_usuario_normal_no_crea_ni_purga(client):
    a = entrar(client, CORREO_A)
    assert client.post(f"/v1/orgs/{ORG_A}/demo", headers=a).status_code == 403
    assert client.delete(f"/v1/orgs/{ORG_A}/demo", headers=a).status_code == 403
