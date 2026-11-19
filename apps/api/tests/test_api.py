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


SALUD = {
    "disk_used_pct": 41.5,
    "cpu_temp_c": 52.3,
    "throttled": 0x50005,
    "clock_synced": True,
    "hw_rev": "proto-b",
    "last_sync_ok_at": "2026-11-19T04:00:00+00:00",
    "last_error": "SerialTimeout: bascula",
}


def _estacion(client, device_id):
    devices = client.get("/v1/devices").json()["devices"]
    return next(d for d in devices if d["device_id"] == device_id)


def test_heartbeat_guarda_la_salud_de_la_estacion():
    client = TestClient(app)
    device_id = f"rpi-salud-{uuid.uuid4().hex[:8]}"
    body = {"pending_count": 2, "agent_version": "0.1.0", "uptime_s": 10, **SALUD}
    assert client.post(f"/v1/devices/{device_id}/heartbeat", json=body).status_code == 200

    d = _estacion(client, device_id)
    for campo, valor in SALUD.items():
        if campo == "last_sync_ok_at":
            assert d[campo].startswith("2026-11-19T04:00:00")
        else:
            assert d[campo] == valor, campo


def test_heartbeat_viejo_sin_campos_nuevos_se_acepta_y_quedan_null():
    client = TestClient(app)
    device_id = f"rpi-viejo-{uuid.uuid4().hex[:8]}"
    viejo = {"pending_count": 0, "agent_version": "0.0.9", "uptime_s": 5}
    assert client.post(f"/v1/devices/{device_id}/heartbeat", json=viejo).status_code == 200

    d = _estacion(client, device_id)
    for campo in SALUD:
        assert d[campo] is None, campo


def test_heartbeat_recorta_error_largo_en_vez_de_rechazar():
    client = TestClient(app)
    device_id = f"rpi-largo-{uuid.uuid4().hex[:8]}"
    body = {"pending_count": 0, "last_error": "x" * 5000}
    assert client.post(f"/v1/devices/{device_id}/heartbeat", json=body).status_code == 200
    assert len(_estacion(client, device_id)["last_error"]) == 1000


def test_base_sqlite_vieja_recibe_las_columnas_de_salud(tmp_path):
    import sqlite3

    from fierro_api.store import SALUD_CAMPOS, ReadingStore

    ruta = tmp_path / "vieja.db"
    conn = sqlite3.connect(ruta)
    conn.execute(
        "CREATE TABLE devices (device_id TEXT PRIMARY KEY, pending_count INTEGER NOT NULL "
        "DEFAULT 0, agent_version TEXT, uptime_s INTEGER, last_seen TEXT NOT NULL)"
    )
    conn.execute("INSERT INTO devices VALUES ('rpi-1', 3, '0.1.0', 9, datetime('now'))")
    conn.commit()
    conn.close()

    store = ReadingStore(str(ruta))
    (d,) = store.list_devices()
    assert d["pending_count"] == 3
    assert all(d[c] is None for c in SALUD_CAMPOS)


def test_heartbeat_con_nan_guarda_null_y_mascara_fuera_de_rango_es_422():
    client = TestClient(app)
    device_id = f"rpi-nan-{uuid.uuid4().hex[:8]}"
    url = f"/v1/devices/{device_id}/heartbeat"
    cuerpo = '{"cpu_temp_c": NaN, "disk_used_pct": Infinity}'
    resp = client.post(url, content=cuerpo, headers={"content-type": "application/json"})
    assert resp.status_code == 200
    d = _estacion(client, device_id)  # GET /v1/devices sigue respondiendo
    assert d["cpu_temp_c"] is None
    assert d["disk_used_pct"] is None

    assert client.post(url, json={"throttled": 2**32}).status_code == 422
    assert client.post(url, json={"throttled": 0xFFFFFFFF}).status_code == 200


def test_heartbeat_limpia_nulos_y_vacios_en_texto():
    client = TestClient(app)
    device_id = f"rpi-nul-{uuid.uuid4().hex[:8]}"
    body = {"last_error": "fallo\x00 serie", "hw_rev": "   ", "clock_synced": False}
    assert client.post(f"/v1/devices/{device_id}/heartbeat", json=body).status_code == 200
    d = _estacion(client, device_id)
    assert d["last_error"] == "fallo serie"
    assert d["hw_rev"] is None
    assert d["clock_synced"] is False
