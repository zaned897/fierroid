"""Donde vive la configuracion de la estacion y como se carga sin prefijos.

Prioridad: variables del proceso > FIERRO_ENV_FILE > archivo del sistema >
apps/device-agent/.env (banco con el repo clonado). Se carga solo el primero
que exista; las variables del proceso nunca se pisan.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

from dotenv import load_dotenv

APP_DIR_NAME = "Fierro"
CONFIG_FILE_NAME = "device.env"
DB_FILE_NAME = "outbox.db"

# src/fierro_device/config.py -> apps/device-agent/.env en instalacion editable.
REPO_ENV_FILE = Path(__file__).resolve().parents[2] / ".env"


def _home() -> Path:
    return Path.home()


def system_config_file() -> Path:
    if sys.platform == "win32":
        base = os.getenv("APPDATA") or str(_home() / "AppData" / "Roaming")
        return Path(base) / APP_DIR_NAME / CONFIG_FILE_NAME
    if sys.platform == "darwin":
        return _home() / "Library" / "Application Support" / APP_DIR_NAME / CONFIG_FILE_NAME
    base = os.getenv("XDG_CONFIG_HOME") or str(_home() / ".config")
    return Path(base) / "fierro" / CONFIG_FILE_NAME


def default_db_path() -> Path:
    """Outbox persistente por sistema. Nunca /tmp: se borra al reiniciar."""
    if sys.platform == "win32":
        base = os.getenv("LOCALAPPDATA") or str(_home() / "AppData" / "Local")
        return Path(base) / APP_DIR_NAME / DB_FILE_NAME
    if sys.platform == "darwin":
        return _home() / "Library" / "Application Support" / APP_DIR_NAME / DB_FILE_NAME
    base = os.getenv("XDG_DATA_HOME") or str(_home() / ".local" / "share")
    return Path(base) / "fierro" / DB_FILE_NAME


class ConfigError(RuntimeError):
    pass


def config_file() -> Path | None:
    """Primer archivo de configuracion aplicable, o None si no hay ninguno."""
    explicito = os.getenv("FIERRO_ENV_FILE")
    if explicito:
        ruta = Path(explicito).expanduser()
        if not ruta.is_file():
            # Pedido explicito que no existe: fallar, no caer a otro archivo.
            raise ConfigError(f"FIERRO_ENV_FILE={explicito} no existe")
        return ruta
    for ruta in (system_config_file(), REPO_ENV_FILE):
        if ruta.is_file():
            return ruta
    return None


def load_config() -> Path | None:
    """Carga el archivo de configuracion en os.environ sin pisar el proceso."""
    ruta = config_file()
    if ruta is not None:
        load_dotenv(ruta, override=False)
    return ruta
