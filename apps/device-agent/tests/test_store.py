from __future__ import annotations

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
