from __future__ import annotations

import os
import uuid

# Isolate API store before app import.
os.environ["FIERRO_API_DB_PATH"] = f"/tmp/fierro-api-test-{uuid.uuid4().hex}.db"

from fastapi.testclient import TestClient
from fierro_api.main import app


def test_health():
    client = TestClient(app)
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["ok"] is True


def test_idempotent_ingest_and_list():
    event_id = f"evt-{uuid.uuid4().hex}"
    reading = {
        "event_id": event_id,
        "device_id": "rpi-test",
        "tag_id": "982000999999999",
        "weight_kg": 355.5,
        "captured_at": "2026-08-24T00:00:00+00:00",
        "stable": True,
        "source": "mock",
    }
    client = TestClient(app)
    r1 = client.post("/v1/readings", json=reading)
    assert r1.status_code == 200
    r2 = client.post("/v1/readings", json={"readings": [reading]})
    assert r2.status_code == 200
    assert event_id in r2.json()["accepted_ids"]
    listed = client.get("/v1/readings")
    assert listed.status_code == 200
    ids = [x["event_id"] for x in listed.json()["readings"]]
    assert ids.count(event_id) == 1

    hb = client.post(
        "/v1/devices/rpi-test/heartbeat",
        json={"pending_count": 0, "agent_version": "0.1.0", "uptime_s": 10},
    )
    assert hb.status_code == 200
    devices = client.get("/v1/devices")
    assert any(d["device_id"] == "rpi-test" for d in devices.json()["devices"])
