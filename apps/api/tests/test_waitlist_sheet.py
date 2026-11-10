"""#129: copia de la lista de espera a Google Sheets, con un cliente falso."""

import os
from uuid import uuid4

import pytest

DSN = os.getenv("FIERRO_TEST_PG_DSN", "")
pytestmark = pytest.mark.skipif(not DSN, reason="PostgreSQL local requerido")


class HojaFalsa:
    def __init__(self, falla=False):
        self.filas: list[list] = []
        self.falla = falla

    def append(self, rows):
        if self.falla:
            raise OSError("Google no responde")
        self.filas.extend(rows)


@pytest.fixture
def base():
    import psycopg
    from fierro_api.migrate import apply_migrations

    apply_migrations(DSN)
    correos = [f"hoja-{uuid4().hex}@example.test" for _ in range(3)]
    with psycopg.connect(DSN) as conn, conn.cursor() as cur:
        # Lo que ya existia en la base de pruebas no es de esta prueba.
        cur.execute("UPDATE waitlist_export SET last_id = "
                    "(SELECT coalesce(max(id), 0) FROM waitlist) WHERE id = 1")
    yield correos
    with psycopg.connect(DSN) as conn, conn.cursor() as cur:
        cur.execute("DELETE FROM waitlist WHERE email = ANY(%s)", (correos,))


def alta(correo, nombre="Rancho"):
    from fierro_api import waitlist

    waitlist.register(DSN, name=nombre, email=correo, stations=3)


def test_altas_nuevas_llegan_una_vez(base):
    from fierro_api.waitlist_sheet import sync

    hoja = HojaFalsa()
    alta(base[0], "=HYPERLINK(\"x\")")
    alta(base[1])
    assert sync(DSN, hoja) == 2
    assert sync(DSN, hoja) == 0  # segunda corrida: nada duplicado

    alta(base[2])
    assert sync(DSN, hoja) == 1
    assert [f[3] for f in hoja.filas] == base
    assert hoja.filas[0][2] == "=HYPERLINK(\"x\")"  # se envia como texto (RAW)
    assert hoja.filas[0][5] == "contact-v1"


def test_caida_de_google_no_pierde_nada(base, caplog):
    import psycopg
    from fierro_api.waitlist_sheet import sync

    alta(base[0])
    with pytest.raises(OSError):
        sync(DSN, HojaFalsa(falla=True))
    assert "No se pudo copiar" in caplog.text

    with psycopg.connect(DSN) as conn, conn.cursor() as cur:
        cur.execute("SELECT count(*) FROM waitlist WHERE email = %s", (base[0],))
        assert cur.fetchone()[0] == 1

    hoja = HojaFalsa()
    assert sync(DSN, hoja) == 1  # el cursor no avanzo: se reintenta
    assert hoja.filas[0][3] == base[0]


def test_el_registro_no_llama_a_google(base, monkeypatch):
    from dataclasses import replace

    from fastapi.testclient import TestClient
    from fierro_api import main, waitlist_sheet

    def prohibido(*a, **k):
        raise AssertionError("POST /v1/waitlist no debe tocar Google")

    monkeypatch.setattr(waitlist_sheet.GoogleSheetsClient, "append", prohibido)
    monkeypatch.setattr(waitlist_sheet, "_token_de_metadatos", prohibido)
    monkeypatch.setattr(main, "settings", replace(main.settings, dsn=DSN))
    body = {"name": "Prueba", "email": base[0], "stations": 2, "consent": True}
    assert TestClient(main.app).post("/v1/waitlist", json=body).status_code == 202


def test_sin_configuracion_el_job_falla_claro(monkeypatch):
    from fierro_api.waitlist_sheet import main

    monkeypatch.delenv("FIERRO_WAITLIST_SHEET_ID", raising=False)
    assert main() == 2
