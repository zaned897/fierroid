"""Salud de la estacion para el heartbeat (#184).

Cada lectura devuelve `None` si no aplica o no se pudo leer (Mac, Windows, CI,
una Pi sin `vcgencmd`): nunca un valor inventado ni 0 por defecto.
"""

from __future__ import annotations

import logging
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

TERMICA = Path("/sys/class/thermal/thermal_zone0/temp")


def disco_usado_pct(db_path: str) -> float | None:
    """% usado de la particion donde vive la outbox."""
    ruta = Path(db_path).parent
    while not ruta.exists() and ruta != ruta.parent:
        ruta = ruta.parent
    try:
        uso = shutil.disk_usage(ruta)
    except OSError:
        return None
    if uso.total <= 0:
        return None
    return round(uso.used * 100 / uso.total, 1)


def temperatura_cpu_c(ruta: Path = TERMICA) -> float | None:
    try:
        return round(int(ruta.read_text().strip()) / 1000, 1)
    except (OSError, ValueError):
        return None


def _comando(*args: str) -> str | None:
    if shutil.which(args[0]) is None:
        return None
    # Sin NOTIFY_SOCKET: las herramientas de systemd (timedatectl) le hablarian
    # al socket del agente como si fueran el agente.
    entorno = {k: v for k, v in os.environ.items() if k != "NOTIFY_SOCKET"}
    try:
        res = subprocess.run(
            args, capture_output=True, text=True, timeout=3, check=False, env=entorno
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if res.returncode != 0:
        return None
    return res.stdout.strip()


def throttling() -> int | None:
    """Mascara de `vcgencmd get_throttled` (salida `throttled=0x50005`)."""
    salida = _comando("vcgencmd", "get_throttled")
    if not salida or "=" not in salida:
        return None
    try:
        return int(salida.split("=", 1)[1], 16)
    except ValueError:
        return None


def reloj_sincronizado() -> bool | None:
    salida = _comando("timedatectl", "show", "-p", "NTPSynchronized", "--value")
    if salida == "yes":
        return True
    if salida == "no":
        return False
    return None


def hw_rev() -> str | None:
    return os.getenv("FIERRO_HW_REV") or None


def leer_salud(db_path: str) -> dict[str, Any]:
    """Campos de salud del heartbeat. Los del agente (ultimo sync, error) van aparte."""
    return {
        "disk_used_pct": disco_usado_pct(db_path),
        "cpu_temp_c": temperatura_cpu_c(),
        "throttled": throttling(),
        "clock_synced": reloj_sincronizado(),
        "hw_rev": hw_rev(),
    }
