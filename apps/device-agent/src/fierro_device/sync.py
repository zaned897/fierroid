from __future__ import annotations

import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)


class CloudSync:
    def __init__(self, api_url: str, device_id: str, timeout_s: float = 10.0) -> None:
        self.api_url = api_url.rstrip("/")
        self.device_id = device_id
        self._client = httpx.Client(timeout=timeout_s)

    def push_readings(self, readings: list[dict[str, Any]]) -> list[str]:
        if not readings:
            return []
        resp = self._client.post(
            f"{self.api_url}/v1/readings",
            json={"readings": readings},
        )
        resp.raise_for_status()
        data = resp.json()
        accepted = data.get("accepted_ids") or [r["event_id"] for r in readings]
        return list(accepted)

    def heartbeat(self, *, pending_count: int, agent_version: str, uptime_s: float) -> None:
        payload = {
            "pending_count": pending_count,
            "agent_version": agent_version,
            "uptime_s": int(uptime_s),
        }
        resp = self._client.post(
            f"{self.api_url}/v1/devices/{self.device_id}/heartbeat",
            json=payload,
        )
        resp.raise_for_status()

    def close(self) -> None:
        self._client.close()
