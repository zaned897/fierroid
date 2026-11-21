from __future__ import annotations

import json
import sqlite3

from fierro_device.models import WeightReading
from fierro_device.store import OutboxStore


def test_outbox_persists_and_marks_synced(tmp_path):
    db = tmp_path / "device.db"
    store = OutboxStore(str(db))
    reading = WeightReading.create(
        device_id="rpi-1",
        tag_id="982000123456789",
        weight_kg=400.25,
        source="mock",
    )
    assert store.save_reading(reading) is True
    assert store.save_reading(reading) is False  # idempotent local
    pending = store.pending()
    assert len(pending) == 1
    assert pending[0]["event_id"] == reading.event_id
    assert store.pending_count() == 1
    store.mark_synced([reading.event_id])
    assert store.pending_count() == 0
    store.close()


def test_migracion_aditiva_con_datos_previos_y_cuarentena_idempotente(tmp_path):
    db = tmp_path / "legacy.db"
    reading = WeightReading.create(
        event_id="pendiente", device_id="rpi-1", tag_id="982000123456789",
        weight_kg=400.25, source="mock",
    )
    # Esquema anterior a la cuarentena, con filas pending y synced reales.
    conn = sqlite3.connect(db)
    conn.executescript("""
        CREATE TABLE readings (
          event_id TEXT PRIMARY KEY, device_id TEXT NOT NULL, tag_id TEXT NOT NULL,
          weight_kg REAL NOT NULL, captured_at TEXT NOT NULL, stable INTEGER NOT NULL,
          source TEXT NOT NULL, payload TEXT NOT NULL,
          status TEXT NOT NULL DEFAULT 'pending',
          created_at TEXT NOT NULL DEFAULT (datetime('now')), synced_at TEXT
        );
    """)
    for event_id, status, synced_at in (
        ("pendiente", "pending", None), ("confirmada", "synced", "2026-01-02 00:00:00"),
    ):
        payload = reading.to_dict() | {"event_id": event_id}
        conn.execute(
            "INSERT INTO readings VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (event_id, reading.device_id, reading.tag_id, reading.weight_kg, reading.captured_at,
             1, "mock", json.dumps(payload), status, "2026-01-01 00:00:00", synced_at),
        )
    conn.commit()
    originales = conn.execute("SELECT * FROM readings ORDER BY event_id").fetchall()
    conn.close()

    for _ in range(2):
        store = OutboxStore(str(db))
        try:
            rows = store._conn.execute("SELECT * FROM readings ORDER BY event_id").fetchall()
            assert [tuple(r)[:11] for r in rows] == originales
            assert all(r["quarantine_reason"] is None for r in rows)
            assert store.pending() == [reading.to_dict()]
        finally:
            store.close()

    motivo = "HTTP 422: peso invalido"
    store = OutboxStore(str(db))
    store.mark_quarantined("pendiente", motivo)
    store.mark_quarantined("confirmada", "no sobrescribir un ACK")
    store.mark_quarantined("pendiente", "no sobrescribir el motivo original")
    store.mark_synced(["pendiente"])  # una cuarentena no se convierte en synced
    assert not store.save_reading(reading)
    store.close()
    store = OutboxStore(str(db))
    try:
        rows = store._conn.execute("SELECT * FROM readings ORDER BY event_id").fetchall()
        assert len(rows) == 2
        assert tuple(rows[0])[:11] == originales[0]
        assert rows[0]["quarantine_reason"] is None
        assert rows[1]["payload"] == originales[1][7]
        assert rows[1]["status"] == "quarantined"
        assert rows[1]["synced_at"] is None
        assert rows[1]["quarantine_reason"] == motivo
        assert store.pending_count() == 0
        assert store.pending() == []
        assert store._conn.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
    finally:
        store.close()
