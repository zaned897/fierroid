import random
from collections.abc import Callable

import pytest
from fierro_device.drivers.peso_simulado import (
    MODO_ALEATORIO,
    MODO_FIJO,
    MODO_POTENCIOMETRO,
    PesoSimulado,
    cuantizar_kg,
    mapear_adc_a_kg,
)
from fierro_device.hardware import HardwareSample


class RelojFalso:
    def __init__(self) -> None:
        self.ahora = 0.0

    def __call__(self) -> float:
        return self.ahora


def adc_fijo(valor: int) -> Callable[[], int]:
    return lambda: valor


def test_fijo_es_estable_cuantizado_y_etiquetado():
    reloj = RelojFalso()
    peso = PesoSimulado(MODO_FIJO, peso_fijo_kg=250.3, clock=reloj)

    muestra = peso.read()

    assert muestra == HardwareSample(
        tag_id=None, weight_kg=250.5, stable=True, source="proto-fijo"
    )


def test_fijo_desde_env_usa_fierro_peso_kg(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("FIERRO_PESO_MODO", "fijo")
    monkeypatch.setenv("FIERRO_PESO_KG", "412")

    muestra = PesoSimulado.from_env().read()

    assert muestra.weight_kg == 412.0
    assert muestra.source == "proto-fijo"
    assert muestra.stable is True


def test_fijo_sin_fierro_peso_kg_falla_ruidoso(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("FIERRO_PESO_MODO", "fijo")
    monkeypatch.delenv("FIERRO_PESO_KG", raising=False)

    with pytest.raises(ValueError, match="FIERRO_PESO_KG"):
        PesoSimulado.from_env()


def test_aleatorio_por_defecto_desde_env(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("FIERRO_PESO_MODO", raising=False)

    peso = PesoSimulado.from_env()

    assert peso.read().source == "proto-aleatorio"


def test_aleatorio_mantiene_valor_durante_permanencia():
    random.seed(7)
    reloj = RelojFalso()
    peso = PesoSimulado(MODO_ALEATORIO, clock=reloj)

    primera = peso.read()
    reloj.ahora = 1.0
    segunda = peso.read()
    reloj.ahora = 3.5
    tercera = peso.read()
    reloj.ahora = 4.6
    cuarta = peso.read()

    assert primera.weight_kg == segunda.weight_kg
    assert tercera.weight_kg != segunda.weight_kg
    assert tercera.stable is False
    assert cuarta.weight_kg == tercera.weight_kg
    assert cuarta.stable is True


def test_aleatorio_valor_plausible_y_cuantizado():
    peso = PesoSimulado(MODO_ALEATORIO, clock=RelojFalso())

    for _ in range(200):
        muestra = peso.read()
        assert 30.0 <= muestra.weight_kg <= 900.0
        assert (muestra.weight_kg * 2) == int(muestra.weight_kg * 2)


def test_potenciometro_mapea_rango_completo_y_cuantiza():
    reloj = RelojFalso()
    bajo = PesoSimulado(MODO_POTENCIOMETRO, adc=adc_fijo(0), clock=reloj).read()
    alto = PesoSimulado(
        MODO_POTENCIOMETRO, adc=adc_fijo(1023), clock=reloj
    ).read()

    assert bajo.weight_kg == 30.0
    assert alto.weight_kg == 900.0
    assert bajo.source == "proto-pot"
    assert alto.source == "proto-pot"


def test_potenciometro_estable_solo_tras_ventana_de_valor_fijo():
    reloj = RelojFalso()
    secuencia = iter([512, 600, 600, 600])
    peso = PesoSimulado(MODO_POTENCIOMETRO, adc=lambda: next(secuencia), clock=reloj)

    primera = peso.read()
    reloj.ahora = 0.5
    girando = peso.read()
    reloj.ahora = 1.2
    asentando = peso.read()
    reloj.ahora = 2.3
    asentado = peso.read()

    assert primera.stable is True
    assert girando.weight_kg != primera.weight_kg
    assert girando.stable is False
    assert asentando.stable is False
    assert asentado.stable is True
    assert asentado.weight_kg == girando.weight_kg


def test_potenciometro_jitter_dentro_de_banda_no_rompe_estabilidad():
    reloj = RelojFalso()
    secuencia = iter([512, 512, 513])
    peso = PesoSimulado(MODO_POTENCIOMETRO, adc=lambda: next(secuencia), clock=reloj)

    primera = peso.read()
    reloj.ahora = 2.0
    con_jitter = peso.read()

    assert primera.stable is True
    assert abs(con_jitter.weight_kg - primera.weight_kg) <= 0.5
    assert con_jitter.stable is True


def test_potenciometro_sin_adc_falla_ruidoso():
    with pytest.raises(ValueError, match="potenciometro sin ADC"):
        PesoSimulado(MODO_POTENCIOMETRO)


def test_modo_desconocido_falla_ruidoso():
    with pytest.raises(ValueError, match="modo desconocido"):
        PesoSimulado("scale")


def test_cuantizar_y_mapear_son_coherentes():
    assert cuantizar_kg(465.2) == 465.0
    assert cuantizar_kg(465.3) == 465.5
    assert mapear_adc_a_kg(0, (30.0, 900.0)) == 30.0
    assert mapear_adc_a_kg(1023, (30.0, 900.0)) == 900.0
    assert mapear_adc_a_kg(512, (30.0, 900.0)) == pytest.approx(
        30.0 + (512 / 1023) * 870.0
    )
