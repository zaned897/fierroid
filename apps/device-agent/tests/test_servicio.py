"""Servicio systemd (#182): synchronous=FULL, sd_notify/watchdog y hardware sin configurar."""

from __future__ import annotations

import os
import socket
import tempfile
import threading
from collections.abc import Iterator
from typing import Any

import pytest
from fierro_device import doctor, notify
from fierro_device import main as agente
from fierro_device.hardware import HardwareSample, SerialHardware
from fierro_device.models import WeightReading
from fierro_device.settings import Settings
from fierro_device.store import OutboxStore


def _settings(db_path: str) -> Settings:
    return Settings(
        device_id="rpi-test",
        db_path=db_path,
        api_url="http://127.0.0.1:9",
        mock_hw=True,
        poll_interval_s=0.01,
        sync_interval_s=0.0,
        sync_max_s=0.0,
        mock_interval_s=3600.0,
        scale_port="/dev/null",
        rfid_port="/dev/null",
    )


class SyncFalso:
    def __init__(self) -> None:
        self.enviados: list[str] = []
        self.heartbeats: list[dict[str, Any]] = []
        self.enviado = threading.Event()
        self.latio = threading.Event()

    def push_readings(self, readings: list[dict[str, Any]]) -> list[str]:
        ids = [r["event_id"] for r in readings]
        self.enviados.extend(ids)
        self.enviado.set()
        return ids

    def heartbeat(self, **kwargs: Any) -> None:
        self.heartbeats.append(kwargs)
        self.latio.set()

    def close(self) -> None:
        pass


class HardwareColgado:
    """Una lectura serie que se bloquea (cable a medias, driver colgado)."""

    def __init__(self) -> None:
        self.liberar = threading.Event()
        self.entro = threading.Event()

    def read(self) -> HardwareSample:
        self.entro.set()
        self.liberar.wait(timeout=10)
        return HardwareSample(None, None, False, "test")


requiere_unix = pytest.mark.skipif(
    not hasattr(socket, "AF_UNIX"), reason="sd_notify es solo Linux (socket AF_UNIX)"
)


@pytest.fixture
def notify_socket(monkeypatch: pytest.MonkeyPatch) -> Iterator[socket.socket]:
    # Ruta corta: AF_UNIX limita a ~108 bytes y tmp_path puede pasarse.
    carpeta = tempfile.mkdtemp(prefix="fierro-")
    ruta = os.path.join(carpeta, "notify")
    sock = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
    sock.bind(ruta)
    sock.settimeout(5)
    monkeypatch.setenv("NOTIFY_SOCKET", ruta)
    yield sock
    sock.close()
    os.unlink(ruta)
    os.rmdir(carpeta)


@pytest.fixture
def agente_en_hilo(tmp_path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("FIERRO_HW_BACKEND", raising=False)
    # signal.signal solo funciona en el hilo principal; aqui el agente corre en otro.
    monkeypatch.setattr(agente.signal, "signal", lambda *_a: None)
    creados: list[tuple[agente.Agent, threading.Thread]] = []

    def crear(hw: Any, sync: Any) -> tuple[agente.Agent, threading.Thread]:
        a = agente.Agent(_settings(str(tmp_path / "device.db")))
        a.sync.close()
        a.hw = hw
        a.sync = sync
        hilo = threading.Thread(target=a.run, daemon=True)
        creados.append((a, hilo))
        return a, hilo

    yield crear
    for a, hilo in creados:
        a.stop()
        if isinstance(a.hw, HardwareColgado):
            a.hw.liberar.set()
        hilo.join(timeout=5)


def test_outbox_usa_synchronous_full(tmp_path):
    store = OutboxStore(str(tmp_path / "device.db"))
    try:
        assert store._conn.execute("PRAGMA synchronous").fetchone()[0] == 2  # FULL
    finally:
        store.close()


def test_sin_notify_socket_no_hace_nada(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("NOTIFY_SOCKET", raising=False)
    assert agente.sd_notify("READY=1") is False


@requiere_unix
def test_avisa_ready_y_luego_watchdog(notify_socket, agente_en_hilo):
    class Quieto:
        def read(self) -> HardwareSample:
            return HardwareSample(None, None, False, "test")

    _a, hilo = agente_en_hilo(Quieto(), SyncFalso())
    hilo.start()
    assert notify_socket.recv(256) == b"READY=1"
    assert notify_socket.recv(256) == b"WATCHDOG=1"


@requiere_unix
def test_lectura_colgada_no_manda_watchdog(notify_socket, agente_en_hilo):
    hw = HardwareColgado()
    _a, hilo = agente_en_hilo(hw, SyncFalso())
    hilo.start()
    assert notify_socket.recv(256) == b"READY=1"
    assert hw.entro.wait(timeout=5)
    notify_socket.settimeout(1.0)
    with pytest.raises(TimeoutError):
        notify_socket.recv(256)
    assert hilo.is_alive()


def test_hardware_sin_configurar_no_sale_y_sigue_sincronizando(agente_en_hilo, monkeypatch):
    monkeypatch.delenv("NOTIFY_SOCKET", raising=False)
    sync = SyncFalso()
    a, hilo = agente_en_hilo(SerialHardware("/dev/null", "/dev/null"), sync)
    lectura = WeightReading.create(
        device_id="rpi-test", tag_id="982000123456789", weight_kg=400.0, source="test"
    )
    assert a.store.save_reading(lectura)
    hilo.start()
    assert sync.enviado.wait(timeout=5)
    assert sync.latio.wait(timeout=5)
    assert hilo.is_alive()
    assert sync.enviados == [lectura.event_id]
    assert "Serial drivers not configured" in (sync.heartbeats[0]["last_error"] or "")
    a.stop()
    hilo.join(timeout=5)
    assert not hilo.is_alive()
    assert OutboxStore(a.settings.db_path).pending_count() == 0


class HardwareSinMensaje:
    def __init__(self) -> None:
        self.lecturas = 0

    def read(self) -> HardwareSample:
        self.lecturas += 1
        raise NotImplementedError


def test_hardware_sin_configurar_se_lee_una_sola_vez(agente_en_hilo, monkeypatch):
    monkeypatch.delenv("NOTIFY_SOCKET", raising=False)
    sync = SyncFalso()
    hw = HardwareSinMensaje()
    a, hilo = agente_en_hilo(hw, sync)
    hilo.start()
    assert sync.latio.wait(timeout=5)
    a.stop()
    hilo.join(timeout=5)
    assert hw.lecturas == 1
    assert sync.heartbeats[0]["last_error"] == "NotImplementedError"


def test_sd_notify_con_socket_roto_no_revienta(monkeypatch, caplog):
    monkeypatch.setenv("NOTIFY_SOCKET", "/no/existe/notify")
    monkeypatch.setattr(notify, "_avisado", False)
    assert notify.sd_notify("WATCHDOG=1") is False
    assert notify.sd_notify("WATCHDOG=1") is False
    assert sum("sd_notify fallo" in r.message for r in caplog.records) == 1


def test_heartbeat_fallido_no_reintenta_en_cada_vuelta(tmp_path, monkeypatch):
    monkeypatch.delenv("FIERRO_HW_BACKEND", raising=False)
    a = agente.Agent(_settings(str(tmp_path / "device.db")))
    a.sync.close()
    intentos = []

    class SinRed(SyncFalso):
        def heartbeat(self, **kwargs: Any) -> None:
            intentos.append(kwargs)
            raise OSError("sin red")

    a.sync = SinRed()
    for _ in range(5):
        a.maybe_heartbeat()
    assert len(intentos) == 1
    a.store.close()


@pytest.mark.skipif(not hasattr(os, "symlink"), reason="requiere enlaces simbolicos")
def test_doctor_reconoce_enlaces_de_udev(tmp_path, monkeypatch):
    real = tmp_path / "ttyUSB0"
    real.write_text("")
    enlace = tmp_path / "fierro-lector"
    enlace.symlink_to(real)

    class Puerto:
        device = str(real)

    from serial.tools import list_ports

    monkeypatch.setattr(list_ports, "comports", lambda: [Puerto()])
    assert doctor._puerto_presente(str(enlace))
    assert doctor._destino_puerto(str(enlace)) == f"{enlace} -> {real}"
    assert doctor._destino_puerto("COM3") == "COM3"
