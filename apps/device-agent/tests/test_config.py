from __future__ import annotations

import os

import pytest
from fierro_device import config
from fierro_device.config import ConfigError, load_config
from fierro_device.main import main
from fierro_device.settings import Settings

VARS = (
    "FIERRO_ENV_FILE",
    "FIERRO_DEVICE_ID",
    "FIERRO_API_URL",
    "FIERRO_MOCK_HW",
    "FIERRO_DB_PATH",
    "FIERRO_HW_BACKEND",
)


@pytest.fixture
def entorno_limpio(monkeypatch, tmp_path):
    for nombre in VARS:
        monkeypatch.delenv(nombre, raising=False)
    # Ningun archivo real de la maquina debe colarse en el test.
    monkeypatch.setattr(config, "system_config_file", lambda: tmp_path / "no-hay.env")
    monkeypatch.setattr(config, "REPO_ENV_FILE", tmp_path / "tampoco.env")
    return tmp_path


def test_sin_configuracion_no_simula_ni_usa_tmp(entorno_limpio):
    settings = Settings.from_env()
    assert settings.mock_hw is False
    assert not settings.db_path.startswith("/tmp")
    assert settings.db_path == str(config.default_db_path())


def test_hardware_real_sin_estacion_ni_api_es_problema(entorno_limpio):
    problemas = Settings.from_env().problems()
    assert any("FIERRO_DEVICE_ID" in p for p in problemas)
    assert any("FIERRO_API_URL" in p for p in problemas)


def test_simulado_explicito_no_exige_estacion(entorno_limpio, monkeypatch):
    monkeypatch.setenv("FIERRO_MOCK_HW", "1")
    assert Settings.from_env().problems() == []


def test_carga_archivo_del_sistema_sin_pisar_el_proceso(entorno_limpio, monkeypatch):
    archivo = entorno_limpio / "device.env"
    archivo.write_text(
        "FIERRO_DEVICE_ID=rpi-los-encinos-002\n"
        "FIERRO_API_URL=https://api.example\n"
        "FIERRO_DB_PATH=${HOME}/outbox.db\n"
    )
    monkeypatch.setattr(config, "system_config_file", lambda: archivo)
    monkeypatch.setenv("FIERRO_API_URL", "http://desde-el-proceso")

    assert load_config() == archivo
    settings = Settings.from_env()
    assert settings.device_id == "rpi-los-encinos-002"
    assert settings.api_url == "http://desde-el-proceso"
    assert settings.db_path == f"{os.environ['HOME']}/outbox.db"


def test_env_file_explicito_inexistente_falla(entorno_limpio, monkeypatch):
    monkeypatch.setenv("FIERRO_ENV_FILE", str(entorno_limpio / "falta.env"))
    with pytest.raises(ConfigError):
        load_config()


def test_main_se_niega_a_arrancar_sin_configuracion(entorno_limpio):
    assert main(["run"]) == 2
