"""Fichas de animales y fotos.

Lo que mas importa aqui no es que la foto se guarde, sino que no se pueda ver
la de otra organizacion y que no se pueda subir un archivo que el navegador
reinterprete como codigo.
"""

from __future__ import annotations

import json
import os
import uuid

import pytest
from fierro_api.animals import MAX_PHOTO_BYTES, PhotoError, validate_photo

DSN = os.getenv("FIERRO_TEST_PG_DSN", "").strip()

PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 64
JPEG = b"\xff\xd8\xff\xe0" + b"\x00" * 64
WEBP = b"RIFF" + b"\x00" * 64


# ---------------------------------------------------------------------------
# Validacion, sin base de datos
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("raw", "tipo"),
    [(PNG, "image/png"), (JPEG, "image/jpeg"), (WEBP, "image/webp")],
)
def test_formatos_aceptados(raw, tipo):
    assert validate_photo(raw, tipo) == tipo


def test_el_tipo_se_normaliza():
    assert validate_photo(PNG, "IMAGE/PNG; charset=binary") == "image/png"


def test_archivo_vacio_se_rechaza():
    with pytest.raises(PhotoError, match="vacio"):
        validate_photo(b"", "image/png")


def test_archivo_demasiado_grande_se_rechaza():
    with pytest.raises(PhotoError, match="maximo"):
        validate_photo(PNG + b"\x00" * MAX_PHOTO_BYTES, "image/png")


def test_svg_se_rechaza():
    """Un SVG puede llevar script dentro y lo serviriamos desde nuestro origen."""
    svg = b'<svg xmlns="http://www.w3.org/2000/svg"><script>alert(1)</script></svg>'
    with pytest.raises(PhotoError, match="JPEG, PNG o WebP"):
        validate_photo(svg, "image/svg+xml")


def test_no_se_cree_el_tipo_declarado_por_el_cliente():
    """Subir HTML diciendo que es JPEG es como se sirve XSS desde tu dominio."""
    html = b"<!doctype html><script>alert(1)</script>"
    with pytest.raises(PhotoError, match="no coincide"):
        validate_photo(html, "image/jpeg")


def test_png_declarado_como_jpeg_se_rechaza():
    with pytest.raises(PhotoError, match="no coincide"):
        validate_photo(PNG, "image/jpeg")


# ---------------------------------------------------------------------------
# Base de datos y endpoints
# ---------------------------------------------------------------------------

pg = pytest.mark.skipif(not DSN, reason="FIERRO_TEST_PG_DSN no definido")

SUFIJO = uuid.uuid4().hex[:8]
TAG_A = f"48411100000{SUFIJO[:4]}"[:15]
TAG_B = f"48422200000{SUFIJO[:4]}"[:15]


@pytest.fixture(scope="module")
def mundo():
    import psycopg
    from fierro_api.auth import create_user
    from fierro_api.migrate import apply_migrations
    from fierro_api.tenancy import build_specs, seed_tenants

    apply_migrations(DSN)
    seed_tenants(DSN, build_specs(orgs=2, ranches_per_org=1, devices_per_ranch=1))

    correos = {
        "a": f"animal-a-{SUFIJO}@fierro.test",
        "b": f"animal-b-{SUFIJO}@fierro.test",
        "su": f"animal-su-{SUFIJO}@fierro.test",
    }
    create_user(DSN, email=correos["a"], password="clave-de-prueba", org_slug="los-encinos")
    create_user(DSN, email=correos["b"], password="clave-de-prueba", org_slug="valle-verde")
    create_user(DSN, email=correos["su"], password="clave-de-prueba", is_superuser=True)

    yield correos

    with psycopg.connect(DSN) as conn, conn.cursor() as cur:
        cur.execute("DELETE FROM animals WHERE tag_id = ANY(%s)", ([TAG_A, TAG_B],))
        cur.execute("DELETE FROM users WHERE email = ANY(%s)", (list(correos.values()),))
        conn.commit()


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
    # El store abre un pool de conexiones: sin cerrarlo, cada prueba deja
    # conexiones vivas y con suficientes pruebas se agota el servidor.
    store.close()


def entrar(client, correo):
    resp = client.post("/v1/auth/login", json={"email": correo, "password": "clave-de-prueba"})
    assert resp.status_code == 200, resp.text
    return {"Authorization": f"Bearer {resp.json()['api_key']}"}


@pg
def test_alta_y_consulta_de_ficha(client, mundo):
    a = entrar(client, mundo["a"])

    resp = client.put(f"/v1/animals/{TAG_A}", json={"alias": "La Pinta"}, headers=a)
    assert resp.status_code == 200
    assert resp.json()["alias"] == "La Pinta"

    detalle = client.get(f"/v1/animals/{TAG_A}", headers=a)
    assert detalle.status_code == 200
    assert detalle.json()["alias"] == "La Pinta"


@pg
def test_una_organizacion_no_ve_la_ficha_de_otra(client, mundo):
    a = entrar(client, mundo["a"])
    b = entrar(client, mundo["b"])

    client.put(f"/v1/animals/{TAG_A}", json={"alias": "De los Encinos"}, headers=a)

    assert client.get(f"/v1/animals/{TAG_A}", headers=b).status_code == 404
    tags_b = [x["tag_id"] for x in client.get("/v1/animals", headers=b).json()["animals"]]
    assert TAG_A not in tags_b


@pg
def test_el_mismo_arete_puede_existir_en_dos_organizaciones(client, mundo):
    """Si un animal se vende, el comprador lleva su propia ficha."""
    a = entrar(client, mundo["a"])
    b = entrar(client, mundo["b"])

    client.put(f"/v1/animals/{TAG_B}", json={"alias": "Nombre viejo"}, headers=a)
    client.put(f"/v1/animals/{TAG_B}", json={"alias": "Nombre nuevo"}, headers=b)

    assert client.get(f"/v1/animals/{TAG_B}", headers=a).json()["alias"] == "Nombre viejo"
    assert client.get(f"/v1/animals/{TAG_B}", headers=b).json()["alias"] == "Nombre nuevo"


@pg
def test_subir_y_recuperar_la_foto(client, mundo):
    a = entrar(client, mundo["a"])

    subida = client.post(
        f"/v1/animals/{TAG_A}/photo",
        files={"file": ("vaca.png", PNG, "image/png")},
        headers=a,
    )
    assert subida.status_code == 200
    assert subida.json()["byte_size"] == len(PNG)

    foto = client.get(f"/v1/animals/{TAG_A}/photo", headers=a)
    assert foto.status_code == 200
    assert foto.content == PNG
    assert foto.headers["content-type"].startswith("image/png")
    # Sin nosniff, el navegador puede reinterpretar contenido de usuario.
    assert foto.headers["x-content-type-options"] == "nosniff"


@pg
def test_la_lista_no_arrastra_el_binario(client, mundo):
    a = entrar(client, mundo["a"])
    client.post(
        f"/v1/animals/{TAG_A}/photo",
        files={"file": ("vaca.png", PNG, "image/png")},
        headers=a,
    )

    body = client.get("/v1/animals", headers=a).json()
    ficha = next(x for x in body["animals"] if x["tag_id"] == TAG_A)

    assert ficha["has_photo"] is True
    assert "bytes" not in json.dumps(body)


@pg
def test_no_se_ve_la_foto_de_otra_organizacion(client, mundo):
    a = entrar(client, mundo["a"])
    b = entrar(client, mundo["b"])

    client.post(
        f"/v1/animals/{TAG_A}/photo",
        files={"file": ("vaca.png", PNG, "image/png")},
        headers=a,
    )

    assert client.get(f"/v1/animals/{TAG_A}/photo", headers=b).status_code == 404


@pg
def test_no_se_borra_la_foto_de_otra_organizacion(client, mundo):
    a = entrar(client, mundo["a"])
    b = entrar(client, mundo["b"])

    client.post(
        f"/v1/animals/{TAG_A}/photo",
        files={"file": ("vaca.png", PNG, "image/png")},
        headers=a,
    )

    assert client.delete(f"/v1/animals/{TAG_A}/photo", headers=b).status_code == 404
    # Sigue ahi para su dueno.
    assert client.get(f"/v1/animals/{TAG_A}/photo", headers=a).status_code == 200


@pg
def test_subir_html_disfrazado_se_rechaza(client, mundo):
    a = entrar(client, mundo["a"])

    resp = client.post(
        f"/v1/animals/{TAG_A}/photo",
        files={"file": ("x.jpg", b"<!doctype html><script>alert(1)</script>", "image/jpeg")},
        headers=a,
    )
    assert resp.status_code == 400
    assert "no coincide" in resp.json()["detail"]


@pg
def test_el_superusuario_debe_indicar_organizacion_para_escribir(client, mundo):
    """Adivinarla seria escribir en el rancho equivocado."""
    su = entrar(client, mundo["su"])

    sin_org = client.put(f"/v1/animals/{TAG_A}", json={"alias": "X"}, headers=su)
    assert sin_org.status_code == 400
    assert "org=" in sin_org.json()["detail"]

    con_org = client.put(
        f"/v1/animals/{TAG_A}?org=los-encinos", json={"alias": "Puesto por admin"}, headers=su
    )
    assert con_org.status_code == 200


@pg
def test_las_fichas_exigen_credencial(client):
    assert client.get("/v1/animals").status_code == 401
    assert client.get(f"/v1/animals/{TAG_A}/photo").status_code == 401
