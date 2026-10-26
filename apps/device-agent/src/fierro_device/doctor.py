"""`fierro-device doctor`: revisa la estacion sin capturar ni tocar la outbox."""

from __future__ import annotations

import os
import sqlite3
from pathlib import Path

import httpx

from fierro_device.settings import Settings


def _pendientes(db_path: str) -> str:
    ruta = Path(db_path)
    if not ruta.exists():
        return "todavia no existe; se crea al arrancar"
    conn = sqlite3.connect(f"{ruta.as_uri()}?mode=ro", uri=True)
    try:
        filas = conn.execute(
            "SELECT status, count(*) FROM readings GROUP BY status"
        ).fetchall()
    finally:
        conn.close()
    return ", ".join(f"{estado}={n}" for estado, n in filas) or "vacia"


def _puerto_presente(puerto: str) -> bool:
    from serial.tools import list_ports

    return any(p.device == puerto for p in list_ports.comports())


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

    try:
        ok(f"outbox {settings.db_path}: {_pendientes(settings.db_path)}")
    except sqlite3.Error as exc:
        falla(f"outbox {settings.db_path}: {exc}")

    if not settings.mock_hw:
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
