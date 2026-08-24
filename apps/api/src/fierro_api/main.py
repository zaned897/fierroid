from __future__ import annotations

from typing import Any

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from fierro_api import __version__
from fierro_api.settings import Settings
from fierro_api.store import ReadingStore

settings = Settings.from_env()
store = ReadingStore(settings.db_path)

app = FastAPI(title="Fierro API", version=__version__)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class WeightReadingIn(BaseModel):
    event_id: str
    device_id: str
    tag_id: str
    weight_kg: float
    captured_at: str
    stable: bool = True
    source: str = "unknown"


class ReadingsBatchIn(BaseModel):
    readings: list[WeightReadingIn] = Field(default_factory=list)


class HeartbeatIn(BaseModel):
    pending_count: int = 0
    agent_version: str | None = None
    uptime_s: int | None = None


@app.get("/health")
def health() -> dict[str, Any]:
    return {"ok": True, "version": __version__}


@app.post("/v1/readings")
def post_readings(body: WeightReadingIn | ReadingsBatchIn) -> dict[str, Any]:
    if isinstance(body, WeightReadingIn):
        items = [body.model_dump()]
    else:
        items = [r.model_dump() for r in body.readings]
    accepted, duplicates = store.upsert_readings(items)
    return {
        "accepted_ids": accepted,
        "duplicate_ids": duplicates,
        "count": len(accepted),
    }


@app.get("/v1/readings")
def get_readings(limit: int = Query(default=50, ge=1, le=500)) -> dict[str, Any]:
    return {"readings": store.list_readings(limit=limit)}


@app.post("/v1/devices/{device_id}/heartbeat")
def post_heartbeat(device_id: str, body: HeartbeatIn) -> dict[str, Any]:
    store.heartbeat(
        device_id,
        pending_count=body.pending_count,
        agent_version=body.agent_version,
        uptime_s=body.uptime_s,
    )
    return {"ok": True, "device_id": device_id}


@app.get("/v1/devices")
def get_devices() -> dict[str, Any]:
    return {"devices": store.list_devices()}


def main() -> None:
    import uvicorn

    uvicorn.run(
        "fierro_api.main:app",
        host=settings.host,
        port=settings.port,
        reload=False,
    )


if __name__ == "__main__":
    main()
