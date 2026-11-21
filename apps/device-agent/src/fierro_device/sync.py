from __future__ import annotations

import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)


class SyncError(RuntimeError):
    """La API respondio sin ACK reconocible: las lecturas quedan `pending`."""


class ReadingRejected(RuntimeError):
    """Rechazo de validacion; sin event_id hay que aislar el lote antes de actuar."""

    def __init__(self, event_id: str | None, reason: str) -> None:
        super().__init__(reason)
        self.event_id = event_id
        self.reason = reason


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
            timeout=httpx.Timeout(connect=5.0, read=15.0, write=5.0, pool=5.0),
            transport=transport,
        )

    def push_readings(self, readings: list[dict[str, Any]]) -> list[str]:
        if not readings:
            return []
        resp = self._client.post(
            f"{self.api_url}/v1/readings",
            json={"readings": readings},
        )
        # Solo errores de validacion. Autenticacion, limites, 5xx y red se reintentan.
        if resp.status_code in (400, 422):
            try:
                rejection = resp.json()
            except ValueError:
                rejection = None
            event_id = None
            if isinstance(rejection, dict):
                event_id = rejection.get("event_id")
                detail = rejection.get("detail")
                if event_id is None and isinstance(detail, dict):
                    event_id = detail.get("event_id")
            if event_id is not None and (
                not isinstance(event_id, str) or event_id not in {r["event_id"] for r in readings}
            ):
                raise SyncError("rechazo con event_id invalido o no enviado")
            # Sin identificacion explicita solo un envio individual permite atribuir el rechazo.
            if event_id is None and len(readings) == 1:
                event_id = readings[0]["event_id"]
            raise ReadingRejected(event_id, f"HTTP {resp.status_code}: {resp.text[:500]}")
        resp.raise_for_status()
        data = resp.json()
        if not isinstance(data, dict):
            raise SyncError("respuesta que no es un objeto JSON")
        listas = [data.get(campo) for campo in ("accepted_ids", "duplicate_ids")]
        if all(lista is None for lista in listas):
            raise SyncError("respuesta sin accepted_ids ni duplicate_ids")
        confirmados: list[str] = []
        for lista in listas:
            if lista is None:
                continue
            # Solo una lista de strings cuenta como ACK: un dict o un str no.
            if not isinstance(lista, list) or not all(isinstance(e, str) for e in lista):
                raise SyncError("accepted_ids/duplicate_ids no son listas de ids")
            confirmados.extend(lista)
        # ACK estricto: solo lo que el servidor confirma tener, y solo lo que enviamos.
        enviados = {r["event_id"] for r in readings}
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
