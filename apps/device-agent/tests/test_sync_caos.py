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
from fierro_device.store import OutboxStore
from fierro_device.sync import CloudSync, SyncError


class ApiFalsa:
    def __init__(self) -> None:
        self.guardados: list[str] = []  # cada event_id guardado, en orden
        self.caida = False
        self.falla_500: Callable[[int], bool] = lambda _n: False
        self.respuesta: Callable[[list[str], list[str]], dict[str, Any]] | None = None
        self.llamadas = 0
        self.rechazo: Callable[[list[str]], httpx.Response | None] | None = None
        self.lotes: list[list[str]] = []

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.llamadas += 1
        if self.caida:
            raise httpx.ConnectError("red caida", request=request)
        if self.falla_500(self.llamadas):
            return httpx.Response(500, json={"detail": "error"})
        if request.url.path.endswith("/heartbeat"):
            return httpx.Response(200, json={"ok": True})
        ids = [r["event_id"] for r in json.loads(request.content)["readings"]]
        self.lotes.append(ids)
        if self.rechazo is not None:
            rechazo = self.rechazo(ids)
            if rechazo is not None:
                return rechazo
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
    for _ in range(5):  # 70 lecturas en lotes de 50
        if not agente.store.pending_count():
            break
        assert agente.flush_outbox() > 0
    assert agente.store.pending_count() == 0
    assert sorted(api.guardados) == sorted(capturados)
    assert len(api.guardados) == len(set(api.guardados))


def test_200_sin_accepted_ids_no_marca_nada(agente, api):
    _capturar(agente, 3)
    api.respuesta = lambda _a, _d: {"ok": True}
    assert agente.flush_outbox() == 0
    assert agente.store.pending_count() == 3


def test_200_con_lista_vacia_no_marca_nada_y_cuenta_como_fallo(agente, api):
    _capturar(agente, 3)
    api.respuesta = lambda _a, _d: {"accepted_ids": [], "duplicate_ids": []}
    assert agente.flush_outbox() == 0
    assert agente.store.pending_count() == 3
    assert agente.backoff.intervalo_s == 4.0  # no vuelve al minimo


@pytest.mark.parametrize(
    "respuesta",
    [
        lambda ids: {"accepted_ids": {i: "rejected" for i in ids}},
        lambda ids: {"accepted_ids": ids[0]},
        lambda ids: {"accepted_ids": [[i] for i in ids]},
        lambda ids: {"accepted_ids": None, "duplicate_ids": None},
        lambda ids: ids,
    ],
)
def test_ack_con_tipos_raros_no_marca_nada(agente, api, respuesta):
    ids = _capturar(agente, 3)
    api.respuesta = lambda _a, _d: respuesta(ids)
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
    for _ in range(20):
        if not agente.store.pending_count():
            break
        agente.flush_outbox()
    assert agente.store.pending_count() == 0
    assert sorted(api.guardados) == sorted(capturados)
    assert len(api.guardados) == len(set(api.guardados))


@pytest.mark.parametrize("codigo", [400, 422])
@pytest.mark.parametrize("identificacion", ["event_id", "detail", "sin_id", "texto"])
def test_lectura_venenosa_no_bloquea_nuevas_y_se_conserva(
    agente, api, codigo, identificacion, caplog,
):
    anteriores = _capturar(agente, 60)
    venenosa = anteriores[17]
    originales = {
        r["event_id"]: r["payload"]
        for r in agente.store._conn.execute("SELECT event_id, payload FROM readings")
    }

    def rechazar(ids):
        if venenosa not in ids:
            return None
        detalle = {"event_id": venenosa, "message": "peso invalido"}
        if identificacion == "texto":
            return httpx.Response(codigo, text="peso invalido")
        cuerpo = {
            "event_id": detalle,
            "detail": {"detail": detalle},
            "sin_id": {"detail": "peso invalido"},
        }[identificacion]
        return httpx.Response(codigo, json=cuerpo)

    api.rechazo = rechazar
    assert agente.flush_outbox() == 0
    assert len(api.lotes[0]) == 50
    assert api.guardados == []  # un rechazo nunca es ACK, ni siquiera de las otras 49
    nuevas = _capturar(agente, 3)
    for _ in range(65):
        if not agente.store.pending_count():
            break
        llamadas = api.llamadas
        agente.flush_outbox()
        assert api.llamadas == llamadas + 1  # deja respirar captura y watchdog

    assert agente.store.pending_count() == 0
    assert set(api.guardados) == set(anteriores + nuevas) - {venenosa}
    assert len(api.guardados) == 62
    assert "quarantined" in caplog.text and venenosa in caplog.text
    # Reinicio: la cuarentena y el motivo son persistentes; ninguna fila desaparece.
    reopened = OutboxStore(agente.settings.db_path)
    try:
        rows = {r["event_id"]: r for r in reopened._conn.execute("SELECT * FROM readings")}
        assert len(rows) == 63
        for event_id, row in rows.items():
            if event_id in originales:
                assert row["payload"] == originales[event_id]
            if event_id == venenosa:
                assert row["status"] == "quarantined"
                assert row["synced_at"] is None
                assert str(codigo) in row["quarantine_reason"]
                assert "peso invalido" in row["quarantine_reason"]
            else:
                assert row["status"] == "synced"
                assert row["synced_at"] is not None
                assert row["quarantine_reason"] is None
    finally:
        reopened.close()


@pytest.mark.parametrize("error", [500, 503, 401, 403, 404, 408, 413, 425, 429, "timeout", "red"])
def test_fallo_transitorio_o_global_no_pone_en_cuarentena(agente, api, error):
    ids = _capturar(agente, 3)

    def fallar(_ids):
        if error == "timeout":
            raise httpx.ReadTimeout("sin respuesta")
        if error == "red":
            raise httpx.ConnectError("sin red")
        return httpx.Response(error, json={"event_id": ids[0], "detail": "fallo"})

    api.rechazo = fallar
    for intervalo in (4.0, 8.0):
        assert agente.flush_outbox() == 0
        assert agente.backoff.intervalo_s == intervalo
        rows = agente.store._conn.execute("SELECT * FROM readings").fetchall()
        assert len(rows) == 3
        assert all(r["status"] == "pending" and r["synced_at"] is None for r in rows)
        assert all(r["quarantine_reason"] is None for r in rows)
    api.rechazo = None
    assert agente.flush_outbox() == 3
    assert agente.backoff.intervalo_s == 2.0


def test_rechazo_con_id_ajeno_no_pone_nada_en_cuarentena(agente, api):
    _capturar(agente, 1)
    api.rechazo = lambda _ids: httpx.Response(
        422, json={"detail": {"event_id": "ajeno", "message": "peso invalido"}},
    )
    assert agente.flush_outbox() == 0
    assert agente.store.pending_count() == 1
    assert agente.backoff.intervalo_s == 4.0


def test_aislamiento_conserva_ack_estricto_y_backoff(agente, api):
    ids = _capturar(agente, 3)
    api.rechazo = lambda enviados: (
        httpx.Response(422, json={"detail": "peso invalido"}) if len(enviados) > 1 else None
    )
    assert agente.flush_outbox() == 0
    assert agente.store.pending_count() == 3  # no adivinar cual de las tres fallo
    api.respuesta = lambda _a, _d: {"accepted_ids": ids[1:] + ["ajeno"]}
    assert agente.flush_outbox() == 0  # no hay ACK del unico id enviado
    assert api.lotes[-1] == ids[:1]
    assert agente.store.pending_count() == 3
    assert agente.backoff.intervalo_s == 8.0
    api.respuesta = None
    assert agente.flush_outbox() == 1  # duplicate_ids confirma el ACK perdido
    assert agente.store.pending_count() == 2


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


def test_timeouts_separados(agente):
    t = agente.sync._client.timeout
    assert (t.connect, t.read, t.write, t.pool) == (5.0, 15.0, 5.0, 5.0)


def test_heartbeat_sigue_su_ritmo_con_el_sync_en_backoff(agente, api, monkeypatch):
    _capturar(agente, 1)
    api.caida = True
    for _ in range(10):
        agente.flush_outbox()
    assert agente.backoff.intervalo_s == 300.0
    latidos = []
    monkeypatch.setattr(agente.sync, "heartbeat", lambda **kw: latidos.append(kw))
    agente.maybe_heartbeat()
    assert len(latidos) == 1


def test_al_arrancar_el_estado_vuelve_al_minimo(agente, api, tmp_path, monkeypatch):
    from fierro_device import doctor
    from fierro_device import main as agente_mod

    monkeypatch.setattr(agente_mod.signal, "signal", lambda *_a: None)

    _capturar(agente, 1)
    api.caida = True
    for _ in range(10):
        agente.flush_outbox()
    db = agente.settings.db_path
    assert "300 s" in doctor._ultimo_sync(db, 2.0)
    assert "nunca" in doctor._ultimo_sync(db, 2.0)

    nuevo = Agent(agente.settings)  # reinicio del servicio
    nuevo._running = False
    nuevo.run()  # arranca y sale: reescribe el estado
    assert leer_estado(db) == {"intervalo_s": 2.0}
    assert doctor._ultimo_sync(str(tmp_path / "no-existe.db"), 2.0) == (
        "ultimo sync OK: nunca; intervalo actual: 2 s"
    )


def test_rechazo_de_todo_no_vacia_la_cola_en_cuarentena(agente, api, caplog):
    """Si el servidor rechaza todo (esquema nuevo, proxy), no se aparta la cola entera."""
    from fierro_device.main import CUARENTENAS_SEGUIDAS_MAX

    ids = _capturar(agente, 20)
    api.rechazo = lambda _ids: httpx.Response(422, json={"detail": "esquema nuevo"})
    for _ in range(30):
        agente.flush_outbox()
    estados = dict(
        agente.store._conn.execute("SELECT event_id, status FROM readings").fetchall()
    )
    en_cuarentena = [e for e in ids if estados[e] == "quarantined"]
    assert len(en_cuarentena) == CUARENTENAS_SEGUIDAS_MAX
    assert agente.store.pending_count() == 20 - CUARENTENAS_SEGUIDAS_MAX
    assert "sin ningun ACK" in caplog.text
    # En cuanto el servidor acepta de nuevo, la cola sigue y el contador se reinicia.
    api.rechazo = None
    for _ in range(30):
        if not agente.store.pending_count():
            break
        agente.flush_outbox()
    assert agente.store.pending_count() == 0
    assert agente._cuarentenas_seguidas == 0
