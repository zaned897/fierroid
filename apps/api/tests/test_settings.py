"""Reglas de configuracion por entorno.

Lo que se prueba aqui no es cosmetico: una API que arranca en produccion sin
Postgres guarda en SQLite efimero y pierde pesajes al primer reinicio. El
invariante raiz dice que eso no puede pasar en silencio.
"""

from __future__ import annotations

import pytest
from fierro_api.settings import ConfigError, Settings

SECRETO_VALIDO = "x" * 48


def make_settings(**overrides) -> Settings:
    base = {
        "db_path": "/tmp/fierro-api.db",
        "host": "0.0.0.0",
        "port": 8000,
        "jwt_secret": SECRETO_VALIDO,
    }
    base.update(overrides)
    return Settings(**base)


def test_dev_arranca_sin_postgres():
    """El flujo de laboratorio del README no debe romperse."""
    make_settings(env="dev").validate()


def test_dev_permite_cors_abierto():
    make_settings(env="dev", cors_origins=("*",)).validate()


@pytest.mark.parametrize("env", ["stage", "production"])
def test_entorno_desplegado_exige_postgres(env):
    with pytest.raises(ConfigError, match="FIERRO_API_DSN"):
        make_settings(env=env, dsn=None, cors_origins=("https://app.fierro.mx",)).validate()


@pytest.mark.parametrize("env", ["stage", "production"])
def test_entorno_desplegado_rechaza_cors_abierto(env):
    with pytest.raises(ConfigError, match="CORS"):
        make_settings(
            env=env,
            dsn="postgresql://fierro@db/fierro",
            cors_origins=("https://app.fierro.mx", "*"),
        ).validate()


@pytest.mark.parametrize("env", ["stage", "production"])
def test_entorno_desplegado_bien_configurado_pasa(env):
    make_settings(
        env=env,
        dsn="postgresql://fierro@db/fierro",
        cors_origins=("https://app.fierro.mx",),
    ).validate()


@pytest.mark.parametrize("env", ["stage", "production"])
def test_entorno_desplegado_exige_secreto_jwt(env):
    """Sin secreto se pueden falsificar tokens de cualquiera, superusuario incluido."""
    with pytest.raises(ConfigError, match="FIERRO_JWT_SECRET"):
        make_settings(
            env=env,
            dsn="postgresql://fierro@db/fierro",
            cors_origins=("https://app.fierro.mx",),
            jwt_secret="",
        ).validate()


@pytest.mark.parametrize("env", ["stage", "production"])
def test_secreto_jwt_corto_se_rechaza(env):
    with pytest.raises(ConfigError, match="32 caracteres"):
        make_settings(
            env=env,
            dsn="postgresql://fierro@db/fierro",
            cors_origins=("https://app.fierro.mx",),
            jwt_secret="corto",
        ).validate()


def test_dev_genera_secreto_aleatorio(monkeypatch):
    """Sin secreto por defecto que alguien pueda heredar a produccion."""
    monkeypatch.delenv("FIERRO_JWT_SECRET", raising=False)
    monkeypatch.setenv("FIERRO_ENV", "dev")

    primero = Settings.from_env()
    segundo = Settings.from_env()

    assert len(primero.jwt_secret) >= 32
    assert primero.jwt_secret != segundo.jwt_secret
    primero.validate()


def test_env_desconocido_falla():
    """Un typo en FIERRO_ENV no debe caer silenciosamente en modo dev."""
    with pytest.raises(ConfigError, match="FIERRO_ENV"):
        make_settings(env="prod").validate()


def test_from_env_parsea_lista_de_origenes(monkeypatch):
    monkeypatch.setenv("FIERRO_ENV", "stage")
    monkeypatch.setenv("FIERRO_JWT_SECRET", SECRETO_VALIDO)
    monkeypatch.setenv("FIERRO_API_DSN", "postgresql://fierro@db/fierro")
    monkeypatch.setenv(
        "FIERRO_API_CORS_ORIGINS", "https://app.fierro.mx, https://ops.fierro.mx ,"
    )

    settings = Settings.from_env()

    assert settings.env == "stage"
    assert settings.cors_origins == ("https://app.fierro.mx", "https://ops.fierro.mx")
    settings.validate()


def test_from_env_normaliza_mayusculas(monkeypatch):
    monkeypatch.setenv("FIERRO_ENV", "PRODUCTION")
    monkeypatch.setenv("FIERRO_API_DSN", "postgresql://fierro@db/fierro")
    monkeypatch.setenv("FIERRO_API_CORS_ORIGINS", "https://app.fierro.mx")

    assert Settings.from_env().env == "production"


def test_dsn_vacio_se_trata_como_ausente(monkeypatch):
    """Una variable declarada pero vacia es el error de despliegue clasico."""
    monkeypatch.setenv("FIERRO_ENV", "production")
    monkeypatch.setenv("FIERRO_JWT_SECRET", SECRETO_VALIDO)
    monkeypatch.setenv("FIERRO_API_DSN", "   ")
    monkeypatch.setenv("FIERRO_API_CORS_ORIGINS", "https://app.fierro.mx")

    with pytest.raises(ConfigError, match="FIERRO_API_DSN"):
        Settings.from_env().validate()
