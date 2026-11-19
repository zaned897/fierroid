"""`fierro-device doctor`: revisa la estacion sin capturar ni tocar la outbox."""

from __future__ import annotations

import os
import sqlite3
from pathlib import Path

import httpx

from fierro_device.backoff import leer_estado
from fierro_device.settings import Settings


def _pendientes(db_path: str) -> str:
    ruta = Path(db_path)
    if not ruta.exists():
        return "todavia no existe; se crea al arrancar"
    conn = sqlite3.connect(f"{ruta.resolve().as_uri()}?mode=ro", uri=True)
    try:
        filas = conn.execute(
            "SELECT status, count(*) FROM readings GROUP BY status"
        ).fetchall()
    finally:
        conn.close()
    return ", ".join(f"{estado}={n}" for estado, n in filas) or "vacia"


def _ultimo_sync(db_path: str, minimo_s: float) -> str:
    ruta = Path(db_path)
    ultimo = None
    if ruta.exists():
        conn = sqlite3.connect(f"{ruta.resolve().as_uri()}?mode=ro", uri=True)
        try:
            ultimo = conn.execute("SELECT max(synced_at) FROM readings").fetchone()[0]
        finally:
            conn.close()
    estado = leer_estado(db_path) or {}
    intervalo = estado.get("intervalo_s")
    if not isinstance(intervalo, int | float) or isinstance(intervalo, bool):
        intervalo = minimo_s
    cuando = f"{ultimo} UTC" if ultimo else "nunca"
    return f"ultimo sync OK: {cuando}; intervalo actual: {intervalo:g} s"


def _puerto_presente(puerto: str) -> bool:
    from serial.tools import list_ports

    # comports() lista /dev/ttyUSB*, no los enlaces de udev (/dev/fierro-lector):
    # comparar contra el destino real.
    real = os.path.realpath(puerto) if os.path.islink(puerto) else puerto
    return any(p.device in (puerto, real) for p in list_ports.comports())


def _destino_puerto(puerto: str) -> str:
    """A que dispositivo real apunta un puerto (los enlaces de udev cambian de destino)."""
    if not os.path.islink(puerto):
        return puerto
    return f"{puerto} -> {os.path.realpath(puerto)}"


def run_doctor(settings: Settings, config_path: Path | None) -> int:
    """Imprime un renglon por chequeo. Devuelve 0 si todo esta bien."""
    fallas = 0

    def ok(msg: str) -> None:
        print(f"[ OK ] {msg}")

    def falla(msg: str) -> None:
        nonlocal fallas
        fallas += 1
        print(f"[FALLA] {msg}")

    if config_path:
        ok(f"configuracion: {config_path}")
    else:
        print("[AVISO] sin archivo de configuracion; solo variables del proceso")

    for problema in settings.problems():
        falla(problema)

    modo = "SIMULADO" if settings.mock_hw else "hardware real"
    backend = os.getenv("FIERRO_HW_BACKEND") or "serial"
    ok(f"estacion={settings.device_id} modo={modo} backend={backend}")
    if not settings.mock_hw and backend == "serial":
        # SerialHardware.read() lanza NotImplementedError: el agente arranca,
        # sincroniza y late, pero no captura.
        falla("backend serial sin drivers: el agente no captura (ver SerialHardware)")

    try:
        ok(f"outbox {settings.db_path}: {_pendientes(settings.db_path)}")
    except sqlite3.Error as exc:
        falla(f"outbox {settings.db_path}: {exc}")
    try:
        print(f"[INFO] {_ultimo_sync(settings.db_path, settings.sync_interval_s)}")
    except sqlite3.Error as exc:
        falla(f"sync {settings.db_path}: {exc}")

    if not settings.mock_hw:
        for nombre, puerto in (("bascula", settings.scale_port), ("lector", settings.rfid_port)):
            print(f"[INFO] puerto {nombre}: {_destino_puerto(puerto)}")
        if _puerto_presente(settings.rfid_port):
            ok(f"puerto {settings.rfid_port} conectado")
        else:
            falla(
                f"puerto {settings.rfid_port} no aparece; "
                "revisar cable de datos o `python -m serial.tools.list_ports -v`"
            )

    try:
        resp = httpx.get(f"{settings.api_url}/health", timeout=10.0)
        resp.raise_for_status()
        env = resp.json().get("env", "?")
        ok(f"API {settings.api_url} responde (env={env})")
    except (httpx.HTTPError, ValueError) as exc:
        falla(f"API {settings.api_url} no responde: {exc}")

    print("Listo para capturar." if fallas == 0 else f"{fallas} problema(s) por resolver.")
    return 0 if fallas == 0 else 1
