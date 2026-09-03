"""Pruebas del store Postgres contra una base real.

Se saltan solas si no hay FIERRO_TEST_PG_DSN. En CI el job `python` levanta un
servicio Postgres y define esa variable, asi que ahi si corren.

    docker compose up -d db
    FIERRO_TEST_PG_DSN=postgresql://fierro:fierro@localhost:5432/fierro pytest apps/api -q
"""

from __future__ import annotations

import os
import uuid
from datetime import datetime, timezone

import pytest

DSN = os.getenv("FIERRO_TEST_PG_DSN", "").strip()

pytestmark = pytest.mark.skipif(not DSN, reason="FIERRO_TEST_PG_DSN no definido")


@pytest.fixture(scope="module")
def store():
    from fierro_api.migrate import apply_migrations
    from fierro_api.store_pg import PostgresReadingStore

    apply_migrations(DSN)  # idempotente: no depende del paso de CI
    instance = PostgresReadingStore(DSN)
    yield instance

    # Limpieza: en CI la base es efimera, pero en local suele ser la de
    # docker compose y no queremos dejarle basura al que la use despues.
    with instance._pool.connection() as conn, conn.cursor() as cur:
        cur.execute("DELETE FROM readings WHERE device_id = 'rpi-pgtest'")
        cur.execute("DELETE FROM devices WHERE device_id LIKE 'rpi-hb-%'")
    instance.close()


def count_rows(store, event_id):
    """Cuenta filas por event_id con SQL directo.

    La unicidad es una propiedad de la tabla, no del listado. list_readings
    devuelve solo las N mas recientes, asi que contra una base poblada las
    filas de prueba caen fuera de la ventana y el assert miente.
    """
    with store._pool.connection() as conn, conn.cursor() as cur:
        cur.execute("SELECT count(*) AS n FROM readings WHERE event_id = %s", (event_id,))
        return cur.fetchone()["n"]


def make_reading(**overrides):
    # captured_at "ahora", como una lectura real: asi la fila entra en la
    # ventana de list_readings aunque la base ya tenga historia.
    reading = {
        "event_id": f"evt-{uuid.uuid4().hex}",
        "device_id": "rpi-pgtest",
        "tag_id": "484000123456789",
        "weight_kg": 412.5,
        "captured_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "stable": True,
        "source": "test",
    }
    reading.update(overrides)
    return reading


def test_reenvio_del_mismo_lote_no_duplica(store):
    """El invariante: reenviar tras un ACK perdido no crea un segundo pesaje."""
    reading = make_reading()

    accepted, duplicates = store.upsert_readings([reading])
    assert accepted == [reading["event_id"]]
    assert duplicates == []

    accepted, duplicates = store.upsert_readings([reading])
    # Sigue aceptado: el device debe poder marcar la fila como synced.
    assert accepted == [reading["event_id"]]
    assert duplicates == [reading["event_id"]]

    assert count_rows(store, reading["event_id"]) == 1


def test_duplicado_dentro_del_mismo_lote(store):
    """Un lote mal armado en el edge no debe reventar el ingest."""
    reading = make_reading()

    accepted, duplicates = store.upsert_readings([reading, reading])
    assert accepted == [reading["event_id"], reading["event_id"]]
    assert duplicates == [reading["event_id"]]

    assert count_rows(store, reading["event_id"]) == 1


def test_lote_vacio_no_toca_la_base(store):
    assert store.upsert_readings([]) == ([], [])


def test_campos_devueltos_respetan_el_contrato(store):
    reading = make_reading(weight_kg=333.0, stable=False, source="synthetic")
    store.upsert_readings([reading])

    row = next(
        r for r in store.list_readings(limit=500) if r["event_id"] == reading["event_id"]
    )
    assert row["weight_kg"] == 333.0
    assert row["stable"] is False
    assert row["source"] == "synthetic"
    assert row["device_id"] == "rpi-pgtest"
    # captured_at viaja como string ISO-8601, igual que en SQLite.
    assert isinstance(row["captured_at"], str)
    assert row["captured_at"] == reading["captured_at"]


def test_captured_at_sin_zona_se_asume_utc(store):
    # UTC pero sin zona: es justo el caso que el store debe interpretar.
    naive = datetime.now(timezone.utc).replace(tzinfo=None, microsecond=0).isoformat()
    reading = make_reading(captured_at=naive)
    accepted, _ = store.upsert_readings([reading])
    assert accepted == [reading["event_id"]]

    row = next(
        r for r in store.list_readings(limit=500) if r["event_id"] == reading["event_id"]
    )
    assert row["captured_at"].endswith("+00:00")


def test_heartbeat_actualiza_en_vez_de_insertar(store):
    device_id = f"rpi-hb-{uuid.uuid4().hex[:8]}"

    store.heartbeat(device_id, pending_count=7, agent_version="0.1.0", uptime_s=60)
    store.heartbeat(device_id, pending_count=0, agent_version="0.2.0", uptime_s=120)

    rows = [d for d in store.list_devices() if d["device_id"] == device_id]
    assert len(rows) == 1
    assert rows[0]["pending_count"] == 0
    assert rows[0]["agent_version"] == "0.2.0"


def test_list_readings_respeta_el_limite(store):
    store.upsert_readings([make_reading() for _ in range(5)])
    assert len(store.list_readings(limit=3)) == 3
