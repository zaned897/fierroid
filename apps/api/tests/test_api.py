from __future__ import annotations

import os
import uuid

# Isolate API store before app import.
os.environ["FIERRO_API_DB_PATH"] = f"/tmp/fierro-api-test-{uuid.uuid4().hex}.db"

from fastapi.testclient import TestClient
from fierro_api.main import app


def make_reading(**overrides):
    reading = {
        "event_id": f"evt-{uuid.uuid4().hex}",
        "device_id": "rpi-test",
        "tag_id": "982000999999999",
        "weight_kg": 355.5,
        "captured_at": "2026-08-24T00:00:00+00:00",
        "stable": True,
        "source": "mock",
    }
    reading.update(overrides)
    return reading


def test_health():
    client = TestClient(app)
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["ok"] is True


def test_ingest_idempotente():
    """Reenviar tras un ACK perdido no duplica y sigue devolviendo aceptado."""
    reading = make_reading()
    client = TestClient(app)

    r1 = client.post("/v1/readings", json=reading)
    assert r1.status_code == 200
    assert r1.json()["duplicate_ids"] == []

    r2 = client.post("/v1/readings", json={"readings": [reading]})
    assert r2.status_code == 200
    # Sigue aceptado: el device debe poder marcarlo como synced.
    assert reading["event_id"] in r2.json()["accepted_ids"]
    assert reading["event_id"] in r2.json()["duplicate_ids"]


def test_el_ingest_no_pide_autenticacion():
    """Las estaciones no tienen usuario, y su API key propia aun no existe.

    Cerrar este camino antes de que exista dejaria a las estaciones sin poder
    reportar, que es exactamente lo que el invariante raiz prohibe.
    """
    client = TestClient(app)

    assert client.post("/v1/readings", json=make_reading()).status_code == 200
    assert (
        client.post(
            "/v1/devices/rpi-test/heartbeat",
            json={"pending_count": 0, "agent_version": "0.1.0", "uptime_s": 10},
        ).status_code
        == 200
    )


def test_en_modo_laboratorio_se_lee_sin_credencial():
    """SQLite no tiene usuarios ni organizaciones: no hay nada que separar.

    Exigir credencial aqui romperia el flujo hello-world del README sin
    proteger nada. Es seguro porque settings.validate() prohibe SQLite en
    stage y production: un entorno desplegado no puede caer en este modo.
    El aislamiento real se prueba en test_aislamiento.py, contra Postgres.
    """
    client = TestClient(app)
    assert client.get("/v1/readings").status_code == 200
    assert client.get("/v1/devices").status_code == 200


def test_el_usuario_de_laboratorio_esta_etiquetado():
    """Para que nadie confunda el modo laboratorio con una sesion real."""
    client = TestClient(app)
    body = client.get("/v1/auth/me").json()
    assert body["email"] == "laboratorio@local"
    assert body["org"] is None
