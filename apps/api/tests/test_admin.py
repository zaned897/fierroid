"""Administración de organizaciones, ranchos, estaciones y usuarios.

Lo que estas pruebas cuidan, por orden de gravedad si se rompe:

1. Que un usuario de organización no pueda administrar nada. Es el control de
   acceso, y hasta este ticket ningún endpoint lo tenía porque no había ninguno.
2. Que registrar una estación haga aparecer sus lecturas bajo la organización
   correcta. Ese es el fallo silencioso del modelo: una estación sin rancho
   acepta pesajes que después no se ven en ninguna vista.
3. Que desactivar a alguien le corte el acceso de verdad, sin borrar su rastro.
"""

from __future__ import annotations

import os
import uuid
from datetime import datetime, timezone

import pytest

DSN = os.getenv("FIERRO_TEST_PG_DSN", "").strip()

pytestmark = pytest.mark.skipif(not DSN, reason="FIERRO_TEST_PG_DSN no definido")

SUFIJO = uuid.uuid4().hex[:8]
ORG = f"admin-{SUFIJO}"
DEVICE = f"rpi-admin-{SUFIJO}"
TAG = f"48490000{SUFIJO[:7]}"


@pytest.fixture(scope="module")
def mundo():
    """Un superusuario, un usuario de organización, y una estación sin rancho.

    La estación arranca **sin asignar** a propósito: es el estado del que salen
    los pesajes invisibles, y lo que estas pruebas tienen que poder arreglar.
    """
    import psycopg
    from fierro_api.auth import create_user
    from fierro_api.migrate import apply_migrations
    from fierro_api.tenancy import build_specs, seed_tenants

    apply_migrations(DSN)
    seed_tenants(DSN, build_specs(orgs=1, ranches_per_org=1, devices_per_ranch=1))

    correo_su = f"admin-su-{SUFIJO}@fierro.test"
    correo_normal = f"admin-normal-{SUFIJO}@fierro.test"
    create_user(DSN, email=correo_su, password="clave-de-prueba", is_superuser=True)
    create_user(
        DSN, email=correo_normal, password="clave-de-prueba", org_slug="los-encinos"
    )

    with psycopg.connect(DSN) as conn, conn.cursor() as cur:
        cur.execute(
            "INSERT INTO devices (device_id, pending_count, last_seen) "
            "VALUES (%s, 0, now()) ON CONFLICT (device_id) DO NOTHING",
            (DEVICE,),
        )
        cur.execute(
            """
            INSERT INTO readings
              (event_id, device_id, tag_id, weight_kg, captured_at, stable, source)
            VALUES (%s, %s, %s, 412.5, %s, true, 'test')
            ON CONFLICT (event_id) DO NOTHING
            """,
            (f"evt-admin-{SUFIJO}", DEVICE, TAG, datetime.now(timezone.utc)),
        )
        conn.commit()

    yield {"su": correo_su, "normal": correo_normal}

    with psycopg.connect(DSN) as conn, conn.cursor() as cur:
        cur.execute("DELETE FROM readings WHERE device_id = %s", (DEVICE,))
        cur.execute("DELETE FROM devices WHERE device_id = %s", (DEVICE,))
        cur.execute(
            "DELETE FROM ranches WHERE org_id IN (SELECT id FROM organizations WHERE slug = %s)",
            (ORG,),
        )
        # Por sufijo y no por lista: dos pruebas crean usuarios propios, y
        # enumerarlos aqui seria olvidarse del siguiente que alguien agregue.
        cur.execute("DELETE FROM api_keys WHERE user_id IN "
                    "(SELECT id FROM users WHERE email LIKE %s)", (f"%-{SUFIJO}@fierro.test",))
        cur.execute("DELETE FROM users WHERE email LIKE %s", (f"%-{SUFIJO}@fierro.test",))
        cur.execute("DELETE FROM organizations WHERE slug = %s", (ORG,))
        conn.commit()


@pytest.fixture
def client(monkeypatch):
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


ENDPOINTS = [
    ("get", "/v1/orgs", None),
    ("post", "/v1/orgs", {"slug": "intento", "name": "Intento"}),
    ("post", "/v1/orgs/los-encinos/ranches", {"slug": "intento", "name": "Intento"}),
    ("put", "/v1/devices/rpi-x", {"org": "los-encinos", "ranch": "san-jose"}),
    ("get", "/v1/users", None),
    ("post", "/v1/users", {"email": "x@y.test"}),
    ("delete", "/v1/users/x@y.test", None),
]


@pytest.mark.parametrize(("metodo", "ruta", "cuerpo"), ENDPOINTS)
def test_usuario_de_organizacion_no_administra(client, mundo, metodo, ruta, cuerpo):
    """403, no 404.

    Esconder la ruta detrás de un 404 suena prudente y no lo es: quien
    administra necesita distinguir "no tengo permiso" de "escribí mal la URL".
    """
    cab = entrar(client, mundo["normal"])
    resp = getattr(client, metodo)(ruta, headers=cab, **({"json": cuerpo} if cuerpo else {}))
    assert resp.status_code == 403, f"{metodo} {ruta} devolvio {resp.status_code}"


def test_sin_credencial_no_pasa(client, mundo):
    assert client.get("/v1/orgs").status_code == 401


def test_la_cadena_completa_hace_visible_al_animal(client, mundo):
    """Organización → rancho → estación, y el animal aparece.

    Es el recorrido entero del modelo. Antes de registrar la estación su pesaje
    existe en la base y no se ve en ninguna parte; después, aparece bajo la
    organización nueva.
    """
    cab = entrar(client, mundo["su"])

    # Antes de registrar la estacion, su pesaje no aparece por ningun lado
    # aunque la fila exista: ese es el fallo silencioso que esto arregla.
    visibles = [a["tag_id"] for a in client.get("/v1/animals", headers=cab).json()["animals"]]
    assert TAG not in visibles

    assert client.post(
        "/v1/orgs", headers=cab, json={"slug": ORG, "name": "Org de prueba"}
    ).status_code == 201
    assert client.post(
        f"/v1/orgs/{ORG}/ranches", headers=cab, json={"slug": "potrero", "name": "Potrero"}
    ).status_code == 201

    resp = client.put(f"/v1/devices/{DEVICE}", headers=cab, json={"org": ORG, "ranch": "potrero"})
    assert resp.status_code == 200, resp.text
    cuerpo = resp.json()
    assert cuerpo["previous_org"] is None
    assert cuerpo["readings_moved"] == 1

    animales = client.get("/v1/animals", headers=cab).json()["animals"]
    mio = next(a for a in animales if a["tag_id"] == TAG)
    assert mio["org"] == ORG


def test_la_estacion_sin_rancho_se_lista_aparte(client, mundo):
    """Verlas es la única forma de notarlas: no dan ningún error."""
    cab = entrar(client, mundo["su"])
    sueltas = client.get("/v1/orgs", headers=cab).json()["unassigned_devices"]
    # Este test corre antes o después del anterior segun el orden; en cualquier
    # caso la clave existe y es una lista de estaciones con su conteo.
    assert isinstance(sueltas, list)
    for d in sueltas:
        assert set(d) == {"device_id", "readings"}


@pytest.mark.parametrize("slug", ["Con Mayusculas", "con espacios", "con_guion_bajo", "-inicial"])
def test_slug_invalido_se_rechaza(client, mundo, slug):
    """Un slug con mayúsculas rompe las URLs de `?org=` y no se ve hasta tarde."""
    cab = entrar(client, mundo["su"])
    resp = client.post("/v1/orgs", headers=cab, json={"slug": slug, "name": "Nombre valido"})
    assert resp.status_code == 400
    assert "slug invalido" in resp.json()["detail"]


def test_organizacion_duplicada_se_rechaza(client, mundo):
    cab = entrar(client, mundo["su"])
    client.post("/v1/orgs", headers=cab, json={"slug": ORG, "name": "Org de prueba"})
    resp = client.post("/v1/orgs", headers=cab, json={"slug": ORG, "name": "Otra vez"})
    assert resp.status_code == 400
    assert "Ya existe" in resp.json()["detail"]


def test_rancho_en_organizacion_inexistente_se_rechaza(client, mundo):
    cab = entrar(client, mundo["su"])
    resp = client.post(
        "/v1/orgs/no-existe-jamas/ranches", headers=cab, json={"slug": "x1", "name": "Nombre"}
    )
    assert resp.status_code == 400


def test_no_puedes_desactivarte_a_ti_mismo(client, mundo):
    """El superusuario que se desactiva deja el sistema sin quien administre."""
    cab = entrar(client, mundo["su"])
    resp = client.delete(f"/v1/users/{mundo['su']}", headers=cab)
    assert resp.status_code == 400
    assert "tu propia cuenta" in resp.json()["detail"]


def test_desactivar_corta_el_acceso_y_conserva_el_rastro(client, mundo):
    """Desactivar, nunca borrar.

    Sus pesajes y su historial siguen teniendo sentido; borrar la fila los
    dejaría colgando de un usuario que ya no existe. Lo que sí desaparece es el
    acceso: sus llaves vivas se revocan en el acto, porque dejarlas activas haría
    que siguiera entrando hasta que caducaran.
    """
    from fierro_api.auth import create_user

    correo = f"efimero-{SUFIJO}@fierro.test"
    create_user(DSN, email=correo, password="clave-de-prueba", org_slug="los-encinos")

    suya = entrar(client, correo)
    assert client.get("/v1/auth/me", headers=suya).status_code == 200

    cab = entrar(client, mundo["su"])
    resp = client.delete(f"/v1/users/{correo}", headers=cab)
    assert resp.status_code == 200, resp.text
    assert resp.json()["is_active"] is False
    assert resp.json()["keys_revoked"] >= 1

    # La llave que funcionaba hace una linea ya no sirve.
    assert client.get("/v1/auth/me", headers=suya).status_code == 401

    # Pero el usuario sigue existiendo, con su alcance intacto.
    usuarios = client.get("/v1/users", headers=cab).json()["users"]
    fila = next(u for u in usuarios if u["email"] == correo)
    assert fila["is_active"] is False
    assert fila["org"] == "los-encinos"


def test_alta_de_usuario_es_idempotente(client, mundo):
    cab = entrar(client, mundo["su"])
    correo = f"alta-{SUFIJO}@fierro.test"
    cuerpo = {"email": correo, "full_name": "Alta Prueba", "org": "los-encinos"}
    assert client.post("/v1/users", headers=cab, json=cuerpo).status_code == 201
    assert client.post("/v1/users", headers=cab, json=cuerpo).status_code == 201

    usuarios = client.get("/v1/users", headers=cab).json()["users"]
    assert len([u for u in usuarios if u["email"] == correo]) == 1
