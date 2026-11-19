"""Caos de red para el sync (#183): ACK estricto, backoff con jitter y cortes de red.

La API falsa (`httpx.MockTransport`) imita `POST /v1/readings`: guarda por `event_id`
y responde `accepted_ids` / `duplicate_ids` como `apps/api`.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any

import httpx
import pytest
from fierro_device.backoff import Backoff, leer_estado
from fierro_device.main import Agent
from fierro_device.models import WeightReading
from fierro_device.settings import Settings
from fierro_device.sync import CloudSync, SyncError


class ApiFalsa:
    def __init__(self) -> None:
        self.guardados: list[str] = []  # cada event_id guardado, en orden
        self.caida = False
        self.falla_500: Callable[[int], bool] = lambda _n: False
        self.respuesta: Callable[[list[str], list[str]], dict[str, Any]] | None = None
        self.llamadas = 0

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.llamadas += 1
        if self.caida:
            raise httpx.ConnectError("red caida", request=request)
        if self.falla_500(self.llamadas):
            return httpx.Response(500, json={"detail": "error"})
        if request.url.path.endswith("/heartbeat"):
            return httpx.Response(200, json={"ok": True})
        ids = [r["event_id"] for r in json.loads(request.content)["readings"]]
        aceptados = [e for e in ids if e not in self.guardados]
        duplicados = [e for e in ids if e in self.guardados]
        self.guardados.extend(aceptados)
        if self.respuesta is not None:
            return httpx.Response(200, json=self.respuesta(aceptados, duplicados))
        return httpx.Response(
            200,
            json={"accepted_ids": aceptados, "duplicate_ids": duplicados, "count": len(aceptados)},
        )


class Reloj:
    def __init__(self) -> None:
        self.t = 1000.0

    def __call__(self) -> float:
        return self.t


def _settings(db_path: str) -> Settings:
    return Settings(
        device_id="rpi-caos",
        db_path=db_path,
        api_url="http://api.falsa",
        mock_hw=True,
        poll_interval_s=0.01,
        sync_interval_s=2.0,
        sync_max_s=300.0,
        mock_interval_s=3600.0,
        scale_port="/dev/null",
        rfid_port="/dev/null",
    )


@pytest.fixture
def api() -> ApiFalsa:
    return ApiFalsa()


@pytest.fixture
def agente(tmp_path, api, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("FIERRO_HW_BACKEND", raising=False)
    reloj = Reloj()
    a = Agent(_settings(str(tmp_path / "device.db")), reloj=reloj, aleatorio=lambda: 1.0)
    a.sync.close()
    a.sync = CloudSync("http://api.falsa", "rpi-caos", transport=httpx.MockTransport(api))
    a.reloj_falso = reloj  # type: ignore[attr-defined]
    yield a
    a.sync.close()
    a.store.close()


def _capturar(a: Agent, n: int) -> list[str]:
    ids = []
    for i in range(n):
        r = WeightReading.create(
            device_id="rpi-caos", tag_id=f"98200000000{i:04d}", weight_kg=400.0 + i, source="test"
        )
        assert a.store.save_reading(r)
        ids.append(r.event_id)
    return ids


def test_red_caida_10_ciclos_y_vuelta_sin_perdidas_ni_duplicados(agente, api):
    capturados: list[str] = []
    api.caida = True
    for _ in range(10):
        capturados += _capturar(agente, 7)
        assert agente.flush_outbox() == 0
    assert agente.store.pending_count() == 70
    api.caida = False
    while agente.store.pending_count():
        assert agente.flush_outbox() > 0
    assert sorted(api.guardados) == sorted(capturados)
    assert len(api.guardados) == len(set(api.guardados))


def test_200_sin_accepted_ids_no_marca_nada(agente, api):
    _capturar(agente, 3)
    api.respuesta = lambda _a, _d: {"ok": True}
    assert agente.flush_outbox() == 0
    assert agente.store.pending_count() == 3


def test_200_con_lista_vacia_no_marca_nada(agente, api):
    _capturar(agente, 3)
    api.respuesta = lambda _a, _d: {"accepted_ids": [], "duplicate_ids": []}
    assert agente.flush_outbox() == 0
    assert agente.store.pending_count() == 3


def test_ack_solo_de_ids_confirmados_y_enviados(agente, api):
    ids = _capturar(agente, 3)
    api.respuesta = lambda _a, _d: {"accepted_ids": [ids[0], "ajeno"], "duplicate_ids": []}
    assert agente.flush_outbox() == 1
    pendientes = {r["event_id"] for r in agente.store.pending()}
    assert pendientes == {ids[1], ids[2]}


def test_duplicados_tambien_pasan_a_synced(agente, api):
    ids = _capturar(agente, 4)
    api.guardados.extend(ids[:2])  # el servidor ya tenia dos (ACK perdido antes)
    assert agente.flush_outbox() == 4
    assert agente.store.pending_count() == 0
    assert len(api.guardados) == 4


def test_500_intermitente(agente, api):
    capturados: list[str] = []
    api.falla_500 = lambda n: n % 2 == 1
    for _ in range(6):
        capturados += _capturar(agente, 5)
        agente.flush_outbox()
    while agente.store.pending_count():
        agente.flush_outbox()
    assert sorted(api.guardados) == sorted(capturados)
    assert len(api.guardados) == len(set(api.guardados))


def test_push_sin_campos_de_ack_lanza():
    def transporte(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"count": 1})

    sync = CloudSync("http://api.falsa", "rpi", transport=httpx.MockTransport(transporte))
    with pytest.raises(SyncError):
        sync.push_readings([{"event_id": "e1"}])
    sync.close()


def test_backoff_crece_hasta_el_tope_y_vuelve_al_minimo(agente, api):
    reloj = agente.reloj_falso
    _capturar(agente, 1)
    api.caida = True
    intervalos = []
    for _ in range(12):
        reloj.t = agente._next_sync
        agente.maybe_sync()
        intervalos.append(agente._next_sync - reloj.t)
    assert intervalos[:4] == [4.0, 8.0, 16.0, 32.0]
    assert intervalos[-1] == 300.0
    assert intervalos == sorted(intervalos)
    assert leer_estado(agente.settings.db_path) == {"intervalo_s": 300.0}

    # Antes de que venza la espera no se reintenta.
    llamadas = api.llamadas
    reloj.t = agente._next_sync - 1
    agente.maybe_sync()
    assert api.llamadas == llamadas

    api.caida = False
    reloj.t = agente._next_sync
    agente.maybe_sync()
    assert agente.store.pending_count() == 0
    assert agente._next_sync - reloj.t == 2.0
    assert leer_estado(agente.settings.db_path) == {"intervalo_s": 2.0}


def test_jitter_reparte_entre_la_mitad_y_el_intervalo():
    assert Backoff(2, 300, aleatorio=lambda: 0.0).espera() == 1.0
    assert Backoff(2, 300, aleatorio=lambda: 1.0).espera() == 2.0
    b = Backoff(2, 300, aleatorio=lambda: 0.5)
    for _ in range(20):
        b.fallo()
    assert b.intervalo_s == 300
    assert b.espera() == 225.0
