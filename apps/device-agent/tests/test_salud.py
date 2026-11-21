"""Salud de la estacion en el heartbeat (#184): null cuando no aplica, nunca 0."""

from __future__ import annotations

import json

import httpx
import pytest
from fierro_device import salud
from fierro_device.main import Agent
from fierro_device.settings import Settings
from fierro_device.sync import CloudSync

CAMPOS = (
    "disk_used_pct",
    "cpu_temp_c",
    "throttled",
    "clock_synced",
    "hw_rev",
    "last_sync_ok_at",
    "last_error",
)


@pytest.fixture
def sin_herramientas_de_pi(monkeypatch: pytest.MonkeyPatch, tmp_path):
    """Como Mac/Windows/CI: sin sensor termico, sin vcgencmd ni timedatectl."""
    monkeypatch.setattr(salud, "TERMICA", tmp_path / "no-existe")
    monkeypatch.setattr(salud.shutil, "which", lambda _cmd: None)
    monkeypatch.delenv("FIERRO_HW_REV", raising=False)


def test_fuera_de_la_pi_los_campos_que_no_aplican_son_null(sin_herramientas_de_pi, tmp_path):
    datos = salud.leer_salud(str(tmp_path / "device.db"))
    assert datos["cpu_temp_c"] is None
    assert datos["throttled"] is None
    assert datos["clock_synced"] is None
    assert datos["hw_rev"] is None
    assert isinstance(datos["disk_used_pct"], float)
    assert 0 <= datos["disk_used_pct"] <= 100


def test_disco_de_ruta_que_aun_no_existe_usa_el_padre(tmp_path):
    assert salud.disco_usado_pct(str(tmp_path / "a" / "b" / "device.db")) is not None


def test_temperatura_en_grados(tmp_path):
    sensor = tmp_path / "temp"
    sensor.write_text("48312\n")
    assert salud.temperatura_cpu_c(sensor) == 48.3
    sensor.write_text("basura")
    assert salud.temperatura_cpu_c(sensor) is None


def test_throttling_y_reloj(monkeypatch: pytest.MonkeyPatch):
    salidas = {
        "vcgencmd": "throttled=0x50005",
        "timedatectl": "yes",
    }
    monkeypatch.setattr(salud, "_comando", lambda *args: salidas.get(args[0]))
    assert salud.throttling() == 0x50005
    salidas["vcgencmd"] = "throttled=0x0"
    assert salud.throttling() == 0  # 0 real de la Pi: sin throttling
    salidas["vcgencmd"] = "throttled=-0x1"
    assert salud.throttling() is None
    assert salud.reloj_sincronizado() is True
    salidas["timedatectl"] = "no"
    assert salud.reloj_sincronizado() is False
    salidas["vcgencmd"] = "error"
    assert salud.throttling() is None


def test_hw_rev_de_variable(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("FIERRO_HW_REV", "proto-b")
    assert salud.hw_rev() == "proto-b"
    monkeypatch.setenv("FIERRO_HW_REV", "   ")
    assert salud.hw_rev() is None


def _script(tmp_path, nombre: str, cuerpo: str):
    ruta = tmp_path / nombre
    ruta.write_text("#!/bin/sh\n" + cuerpo + "\n")
    ruta.chmod(0o755)
    return ruta


@pytest.mark.skipif(not hasattr(salud.os, "fork"), reason="scripts sh solo en POSIX")
def test_comando_sin_notify_socket_y_fallas(tmp_path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("NOTIFY_SOCKET", "/run/systemd/notify")
    monkeypatch.setenv("PATH", f"{tmp_path}:{salud.os.environ['PATH']}")
    _script(tmp_path, "eco-socket", 'echo "${NOTIFY_SOCKET:-sin}"')
    _script(tmp_path, "falla", "exit 3")
    _script(tmp_path, "lento", "sleep 5")
    assert salud._comando("eco-socket") == "sin"
    assert salud._comando("falla") is None
    assert salud._comando("lento") is None  # timeout de 2 s
    assert salud._comando("no-existe-fierro") is None


def test_disco_con_error_de_lectura_es_null(monkeypatch: pytest.MonkeyPatch):
    def roto(_ruta):
        raise PermissionError("EACCES")

    monkeypatch.setattr(salud.shutil, "disk_usage", roto)
    assert salud.disco_usado_pct("/data/fierro/device.db") is None


def test_heartbeat_lleva_la_salud_y_el_ultimo_sync(
    sin_herramientas_de_pi, tmp_path, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.delenv("FIERRO_HW_BACKEND", raising=False)
    latidos: list[dict] = []

    def api(request: httpx.Request) -> httpx.Response:
        cuerpo = json.loads(request.content)
        if request.url.path.endswith("/heartbeat"):
            latidos.append(cuerpo)
            return httpx.Response(200, json={"ok": True})
        ids = [r["event_id"] for r in cuerpo["readings"]]
        return httpx.Response(200, json={"accepted_ids": ids, "duplicate_ids": []})

    settings = Settings(
        device_id="rpi-salud",
        db_path=str(tmp_path / "device.db"),
        api_url="http://api.falsa",
        mock_hw=True,
        poll_interval_s=0.01,
        sync_interval_s=2.0,
        sync_max_s=300.0,
        mock_interval_s=0.0,
        scale_port="/dev/null",
        rfid_port="/dev/null",
    )
    a = Agent(settings)
    a.sync.close()
    a.sync = CloudSync("http://api.falsa", "rpi-salud", transport=httpx.MockTransport(api))

    a.maybe_heartbeat()
    assert set(CAMPOS) <= set(latidos[0])
    assert latidos[0]["last_sync_ok_at"] is None
    assert latidos[0]["last_error"] is None
    for campo in ("cpu_temp_c", "throttled", "clock_synced", "hw_rev"):
        assert latidos[0][campo] is None, campo

    assert a.capture_once() is not None
    assert a.flush_outbox() == 1
    a._last_heartbeat = float("-inf")
    a.maybe_heartbeat()
    assert latidos[1]["last_sync_ok_at"] is not None

    # Reinicio con la outbox ya vacia: no se pierde el ultimo sync.
    reiniciado = Agent(settings)
    assert reiniciado._last_sync_ok_at is not None
    assert reiniciado._last_sync_ok_at.endswith("+00:00")
    reiniciado.sync.close()
    reiniciado.store.close()
    a.sync.close()
    a.store.close()


def test_last_error_vive_hasta_el_siguiente_heartbeat(tmp_path, monkeypatch):
    monkeypatch.delenv("FIERRO_HW_BACKEND", raising=False)
    settings = Settings(
        device_id="rpi-err",
        db_path=str(tmp_path / "device.db"),
        api_url="http://api.falsa",
        mock_hw=True,
        poll_interval_s=0.01,
        sync_interval_s=2.0,
        sync_max_s=300.0,
        mock_interval_s=0.0,
        scale_port="/dev/null",
        rfid_port="/dev/null",
    )
    a = Agent(settings)
    latidos: list[dict] = []
    monkeypatch.setattr(a.sync, "heartbeat", lambda **kw: latidos.append(kw))
    a._last_error = "SerialTimeout: bascula"
    a.maybe_heartbeat()
    a._last_heartbeat = float("-inf")
    a.maybe_heartbeat()
    assert [x["last_error"] for x in latidos] == ["SerialTimeout: bascula", None]

    # Un error persistente (hardware sin configurar) se sigue reportando.
    a._hw_error = "sin drivers"
    a._last_error = "sin drivers"
    for _ in range(2):
        a._last_heartbeat = float("-inf")
        a.maybe_heartbeat()
    assert [x["last_error"] for x in latidos[2:]] == ["sin drivers", "sin drivers"]
    a.sync.close()
    a.store.close()
