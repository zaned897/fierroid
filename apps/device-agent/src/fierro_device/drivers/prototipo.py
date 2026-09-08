"""Prototype backend: composes the tag side (#46) with the weight side (#47).

Two realities meet here, and the class is honest about both:

- The bench micro already pairs tag and weight inside each W line (its
  session logic is signal conditioning, like a commercial indicator). Those
  samples pass through untouched; a weight demoted by the micro's timeout
  stays stable=False and never becomes a reading upstream.
- If a tag ever arrives without a weight (a tag-only RFID driver), the
  ticket #48 matching rule applies: the tag opens a capture window (5 s),
  the weight must stabilize inside it, a second distinct tag restarts the
  window (the new animal wins), and a window that closes without a stable
  weight emits nothing and logs why. A tag without a weight is not a weighing.

Selection is by FIERRO_HW_BACKEND=prototipo in build_hardware(); with
FIERRO_MOCK_HW=1 the RFID side runs on the virtual micro and everything is
labeled proto-sim.
"""

from __future__ import annotations

import logging
import time
from collections.abc import Callable

from fierro_device.drivers.micro_simulado import MicroSimulado
from fierro_device.drivers.peso_simulado import PesoSimulado
from fierro_device.drivers.rc522_serie import PuertoSerie, Rc522Serie
from fierro_device.hardware import HardwareBackend, HardwareSample

logger = logging.getLogger("fierro_device")

FUENTE_PROTOTIPO_SIM = "proto-sim"


class PrototipoHardware:
    """HardwareBackend for the prototype: RFID tag + weight, paired."""

    def __init__(
        self,
        rfid: HardwareBackend,
        peso: HardwareBackend | None = None,
        *,
        ventana_s: float = 5.0,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._rfid = rfid
        self._peso = peso
        self._ventana_s = ventana_s
        self._clock = clock
        self._tag_actual: str | None = None
        self._ventana_desde = 0.0

    def read(self) -> HardwareSample:
        muestra = self._rfid.read()
        if muestra.tag_id is None or muestra.weight_kg is not None:
            return muestra
        return self._emparejar(muestra)

    def _emparejar(self, tag: HardwareSample) -> HardwareSample:
        ahora = self._clock()
        if tag.tag_id != self._tag_actual:
            logger.info("ventana de captura abierta para %s", tag.tag_id)
            self._tag_actual = tag.tag_id
            self._ventana_desde = ahora
        elif ahora - self._ventana_desde >= self._ventana_s:
            logger.warning(
                "ventana vencida sin peso estable para %s: no se emite",
                tag.tag_id,
            )
            self._tag_actual = None
            return HardwareSample(None, None, False, tag.source)
        if self._peso is None:
            return HardwareSample(None, None, False, tag.source)
        peso = self._peso.read()
        if peso.weight_kg is None or not peso.stable:
            return HardwareSample(None, None, False, tag.source)
        return HardwareSample(
            tag_id=tag.tag_id,
            weight_kg=peso.weight_kg,
            stable=True,
            source=peso.source,
        )


def construir_prototipo(*, mock: bool, rfid_port: str) -> PrototipoHardware:
    peso = PesoSimulado.from_env()
    if mock:
        rfid: HardwareBackend = Rc522Serie(
            MicroSimulado(auto_intervalo_s=3.0), fuente=FUENTE_PROTOTIPO_SIM
        )
    else:
        rfid = Rc522Serie(PuertoSerie(rfid_port))
    return PrototipoHardware(rfid, peso)
