"""Simulated weight source for the prototype (ticket #47).

Decision written down as the ticket requires: the potentiometer rides on a
microcontroller (Arduino/Pico) streaming 10-bit ADC samples over USB-CDC
serial, not on an MCP3008 over SPI. The bench already crosses serial for the
RFID path, one transport keeps the prototype honest and debuggable, and no
kernel SPI setup is needed on the Pi or the Windows bench. The transport
never reaches this module: the ADC enters as an injected callable, so it can
be swapped for an MCP3008 later without touching stability logic.

This is a declared simulator, not disguised fake data: every sample carries
source proto-pot / proto-fijo / proto-aleatorio, never scale, so prototype
rows are distinguishable from real scale rows in the database. tag_id stays
None; composing tag + weight is ticket #48.
"""

from __future__ import annotations

import os
import random
import time
from collections.abc import Callable

from fierro_device.hardware import HardwareSample

MODO_POTENCIOMETRO = "potenciometro"
MODO_FIJO = "fijo"
MODO_ALEATORIO = "aleatorio"

MODOS = (MODO_POTENCIOMETRO, MODO_FIJO, MODO_ALEATORIO)

FUENTE_POR_MODO: dict[str, str] = {
    MODO_POTENCIOMETRO: "proto-pot",
    MODO_FIJO: "proto-fijo",
    MODO_ALEATORIO: "proto-aleatorio",
}

RANGO_KG: tuple[float, float] = (30.0, 900.0)
PASO_KG = 0.5
ADC_MAX = 1023


def cuantizar_kg(kg: float) -> float:
    return round(kg / PASO_KG) * PASO_KG


def mapear_adc_a_kg(raw: int, rango_kg: tuple[float, float]) -> float:
    bajo, alto = rango_kg
    return bajo + (raw / ADC_MAX) * (alto - bajo)


class PesoSimulado:
    """Weight half of the prototype backend, in three modes.

    Stability mirrors a real animal on the scale: while the value moves
    beyond the +/-0.5 kg band, stable is False; it turns True only after the
    value holds inside the band for a full window (1 s by default).
    """

    def __init__(
        self,
        modo: str,
        *,
        adc: Callable[[], int] | None = None,
        peso_fijo_kg: float | None = None,
        rango_kg: tuple[float, float] = RANGO_KG,
        ventana_s: float = 1.0,
        permanencia_s: float = 3.0,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        if modo not in MODOS:
            raise ValueError(
                f"modo desconocido: {modo!r}; use uno de {', '.join(MODOS)}"
            )
        if modo == MODO_POTENCIOMETRO and adc is None:
            raise ValueError(
                "modo potenciometro sin ADC: inyecta adc (p. ej. el lector serie "
                "del micro) o usa FIERRO_PESO_MODO=fijo|aleatorio"
            )
        if modo == MODO_FIJO and peso_fijo_kg is None:
            raise ValueError("modo fijo sin FIERRO_PESO_KG: falta el valor fijo")
        self._modo = modo
        self._adc = adc
        self._peso_fijo_kg = peso_fijo_kg
        self._rango_kg = rango_kg
        self._ventana_s = ventana_s
        self._permanencia_s = permanencia_s
        self._clock = clock
        self._ancla_kg: float | None = None
        self._estable_desde = float("-inf")
        self._valor_aleatorio: float | None = None
        self._aleatorio_hasta = 0.0

    @classmethod
    def from_env(
        cls, *, adc: Callable[[], int] | None = None
    ) -> PesoSimulado:
        modo = os.getenv("FIERRO_PESO_MODO", MODO_ALEATORIO)
        peso_fijo: float | None = None
        if modo == MODO_FIJO:
            crudo = os.getenv("FIERRO_PESO_KG")
            if crudo is None:
                raise ValueError(
                    "FIERRO_PESO_MODO=fijo requiere FIERRO_PESO_KG"
                )
            peso_fijo = float(crudo)
        return cls(modo, adc=adc, peso_fijo_kg=peso_fijo)

    def read(self) -> HardwareSample:
        if self._modo == MODO_FIJO:
            peso = self._peso_fijo_kg
            if peso is None:
                raise RuntimeError("modo fijo sin peso fijo configurado")
            kg = cuantizar_kg(peso)
        elif self._modo == MODO_ALEATORIO:
            kg = self._siguiente_aleatorio()
        else:
            adc = self._adc
            if adc is None:
                raise RuntimeError("modo potenciometro sin ADC inyectado")
            kg = cuantizar_kg(mapear_adc_a_kg(adc(), self._rango_kg))
        return HardwareSample(
            tag_id=None,
            weight_kg=kg,
            stable=self._evaluar_estabilidad(kg),
            source=FUENTE_POR_MODO[self._modo],
        )

    def _siguiente_aleatorio(self) -> float:
        ahora = self._clock()
        guardado = self._valor_aleatorio
        if guardado is not None and ahora < self._aleatorio_hasta:
            return guardado
        bajo, alto = self._rango_kg
        self._valor_aleatorio = cuantizar_kg(random.uniform(bajo, alto))
        self._aleatorio_hasta = ahora + self._permanencia_s
        return self._valor_aleatorio

    def _evaluar_estabilidad(self, kg: float) -> bool:
        ancla = self._ancla_kg
        if ancla is None:
            self._ancla_kg = kg
        elif abs(kg - ancla) > PASO_KG:
            self._ancla_kg = kg
            self._estable_desde = self._clock()
        return (self._clock() - self._estable_desde) >= self._ventana_s
