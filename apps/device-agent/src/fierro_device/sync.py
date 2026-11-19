from __future__ import annotations

import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)


class SyncError(RuntimeError):
    """La API respondio sin ACK reconocible: las lecturas quedan `pending`."""


class CloudSync:
    def __init__(
        self,
        api_url: str,
        device_id: str,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self.api_url = api_url.rstrip("/")
        self.device_id = device_id
        # Conexion corta para detectar red caida rapido; lectura mas holgada para 4G.
        self._client = httpx.Client(
            timeout=httpx.Timeout(15.0, connect=5.0), transport=transport
        )

    def push_readings(self, readings: list[dict[str, Any]]) -> list[str]:
        if not readings:
            return []
        resp = self._client.post(
            f"{self.api_url}/v1/readings",
            json={"readings": readings},
        )
        resp.raise_for_status()
        data = resp.json()
        if not isinstance(data, dict) or (
            "accepted_ids" not in data and "duplicate_ids" not in data
        ):
            raise SyncError("respuesta sin accepted_ids ni duplicate_ids")
        # ACK estricto: solo lo que el servidor confirma tener, y solo lo que enviamos.
        enviados = {r["event_id"] for r in readings}
        confirmados = list(data.get("accepted_ids") or []) + list(
            data.get("duplicate_ids") or []
        )
        return list(dict.fromkeys(e for e in confirmados if e in enviados))

    def heartbeat(
        self,
        *,
        pending_count: int,
        agent_version: str,
        uptime_s: float,
        last_error: str | None = None,
    ) -> None:
        payload: dict[str, Any] = {
            "pending_count": pending_count,
            "agent_version": agent_version,
            "uptime_s": int(uptime_s),
            "last_error": last_error,
        }
        resp = self._client.post(
            f"{self.api_url}/v1/devices/{self.device_id}/heartbeat",
            json=payload,
        )
        resp.raise_for_status()

    def close(self) -> None:
        self._client.close()
