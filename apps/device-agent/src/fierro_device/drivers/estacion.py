"""Station backend: pairs FDX-B ear tags with stabilized cattle weights (issue #181).

In a real weighing alley, the RFID reader and the scale indicator arrive over
two independent RS485 ports at different rates. EstacionHardware converts those
two streams into a single HardwareSample(tag_id, weight_kg, stable=True) per
animal:

- Opens a capture window on the first tag; a second distinct tag inside the
  same window annuls it and logs "dos aretes en ventana".
- Filters continuous weight samples through FiltroEstable and requires
  weight_kg >= peso_min_kg before emitting.
- After emitting, disarms until the platform drops below cero_kg, so an animal
  standing on the scale for 60 s produces only one weighing.
- Logs the explicit reason for every discard (ventana vencida, dos aretes,
  bajo minimo, sin regreso a cero).

Selected via FIERRO_HW_BACKEND=estacion in build_hardware(). With
FIERRO_MOCK_HW=1 it runs on declared simulated sources labeled estacion-sim
(never scale); without real drivers configured it fails loudly like
SerialHardware.
"""

from __future__ import annotations

import logging
import random
import time
from collections.abc import Callable

from fierro_device.drivers.estabilidad import FiltroEstable
from fierro_device.drivers.ventana import VentanaCaptura
from fierro_device.hardware import HardwareBackend, HardwareSample, SerialHardware
from fierro_device.settings import (
    DEFAULT_CERO_KG,
    DEFAULT_ESTABLE_BANDA_KG,
    DEFAULT_ESTABLE_VENTANA_S,
    DEFAULT_PESO_MIN_KG,
    DEFAULT_VENTANA_TAG_S,
    Settings,
)

logger = logging.getLogger("fierro_device")

FUENTE_ESTACION_SIM = "estacion-sim"

TAGS_ESTACION_SIM: tuple[str, ...] = (
    "982000111111111",
    "982000222222222",
    "982000333333333",
    "982000444444444",
)


class EstacionHardware:
    """HardwareBackend that pairs independent RFID and scale streams."""

    def __init__(
        self,
        rfid: HardwareBackend,
        bascula: HardwareBackend,
        *,
        banda_kg: float = DEFAULT_ESTABLE_BANDA_KG,
        ventana_estable_s: float = DEFAULT_ESTABLE_VENTANA_S,
        peso_min_kg: float = DEFAULT_PESO_MIN_KG,
        cero_kg: float = DEFAULT_CERO_KG,
        ventana_tag_s: float = DEFAULT_VENTANA_TAG_S,
        fuente: str | None = None,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        if peso_min_kg < 0:
            raise ValueError(f"peso_min_kg debe ser >= 0, recibido {peso_min_kg}")
        if cero_kg < 0:
            raise ValueError(f"cero_kg debe ser >= 0, recibido {cero_kg}")
        self._rfid = rfid
        self._bascula = bascula
        self._peso_min_kg = peso_min_kg
        self._cero_kg = cero_kg
        self._fuente = fuente
        self._filtro = FiltroEstable(
            banda_kg=banda_kg,
            ventana_s=ventana_estable_s,
            clock=clock,
        )
        self._ventana = VentanaCaptura(ventana_s=ventana_tag_s, clock=clock)
        self._armada = True
        self._aviso_sin_cero_tag: str | None = None
        self._aviso_bajo_minimo = False

    def read(self) -> HardwareSample:
        m_rfid = self._rfid.read()
        m_peso = self._bascula.read()
        fuente = self._fuente or m_peso.source or m_rfid.source
        vacia = HardwareSample(None, None, False, fuente)

        kg = m_peso.weight_kg
        estable = self._filtro.evaluar(kg) if kg is not None else False
        tag_entrante = m_rfid.tag_id or None

        if not self._armada:
            if kg is not None and kg < self._cero_kg:
                self._armada = True
                self._aviso_sin_cero_tag = None
                logger.info(
                    "regreso a cero (%.1f kg < %.1f kg): estacion armada",
                    kg,
                    self._cero_kg,
                )
            else:
                if tag_entrante is not None and tag_entrante != self._aviso_sin_cero_tag:
                    self._aviso_sin_cero_tag = tag_entrante
                    peso_txt = f"{kg:.1f} kg" if kg is not None else "sin lectura"
                    logger.warning(
                        "pesaje descartado para %s: sin regreso a cero (peso=%s, umbral=%.1f kg)",
                        tag_entrante,
                        peso_txt,
                        self._cero_kg,
                    )
                return vacia

        if self._ventana.abierta and self._ventana.vencida():
            era_anulada = self._ventana.anulada
            tag_vencido = self._ventana.cerrar()
            self._aviso_bajo_minimo = False
            if not era_anulada:
                logger.warning(
                    "ventana vencida sin peso estable para %s: no se emite",
                    tag_vencido,
                )
            if tag_entrante is None or tag_entrante == tag_vencido:
                return vacia

        if self._ventana.anulada:
            return vacia

        if tag_entrante is not None:
            if not self._ventana.abierta:
                logger.info("ventana de captura abierta para %s", tag_entrante)
                self._ventana.abrir(tag_entrante)
                self._aviso_bajo_minimo = False
            elif tag_entrante != self._ventana.tag:
                logger.warning(
                    "ventana anulada (%s y %s): dos aretes en ventana",
                    self._ventana.tag,
                    tag_entrante,
                )
                self._ventana.anular()
                return vacia

        tag_activo = self._ventana.tag
        if tag_activo is None or kg is None or not estable:
            return vacia

        if kg < self._peso_min_kg:
            if not self._aviso_bajo_minimo:
                self._aviso_bajo_minimo = True
                logger.warning(
                    "pesaje descartado para %s: peso bajo minimo (%.1f kg < %.1f kg)",
                    tag_activo,
                    kg,
                    self._peso_min_kg,
                )
            return vacia

        self._ventana.cerrar()
        self._aviso_bajo_minimo = False
        self._armada = False
        return HardwareSample(
            tag_id=tag_activo,
            weight_kg=kg,
            stable=True,
            source=fuente,
        )


class _CorralSimulado:
    """Clock-driven simulated alley cycle for FIERRO_MOCK_HW=1 station mode."""

    def __init__(
        self,
        *,
        duracion_animal_s: float,
        duracion_vacio_s: float,
        peso_min_kg: float,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._duracion_animal_s = duracion_animal_s
        self._periodo_s = duracion_animal_s + duracion_vacio_s
        self._bajo_kg = max(peso_min_kg + 50.0, 280.0)
        self._alto_kg = max(self._bajo_kg + 100.0, 620.0)
        self._clock = clock
        self._inicio = clock()
        self._ciclo = -1
        self._tag = TAGS_ESTACION_SIM[0]
        self._peso_kg = self._bajo_kg

    def estado(self) -> tuple[str | None, float]:
        transcurrido = max(0.0, self._clock() - self._inicio)
        ciclo = int(transcurrido // self._periodo_s)
        if ciclo != self._ciclo:
            self._ciclo = ciclo
            self._tag = TAGS_ESTACION_SIM[ciclo % len(TAGS_ESTACION_SIM)]
            self._peso_kg = round(random.uniform(self._bajo_kg, self._alto_kg) * 2) / 2
        en_ciclo = transcurrido % self._periodo_s
        if en_ciclo < self._duracion_animal_s:
            return self._tag, self._peso_kg
        return None, 0.0


class _RfidSimuladoEstacion:
    def __init__(self, corral: _CorralSimulado) -> None:
        self._corral = corral

    def read(self) -> HardwareSample:
        tag, _ = self._corral.estado()
        return HardwareSample(tag, None, False, FUENTE_ESTACION_SIM)


class _BasculaSimuladaEstacion:
    def __init__(self, corral: _CorralSimulado) -> None:
        self._corral = corral

    def read(self) -> HardwareSample:
        _, peso_kg = self._corral.estado()
        return HardwareSample(None, peso_kg, False, FUENTE_ESTACION_SIM)


def construir_estacion(
    *,
    mock: bool,
    scale_port: str,
    rfid_port: str,
    mock_interval_s: float = 3.0,
    settings: Settings | None = None,
    clock: Callable[[], float] = time.monotonic,
) -> EstacionHardware:
    cfg = settings or Settings.from_env()
    if mock:
        duracion_animal = max(cfg.estable_ventana_s + 0.5, mock_interval_s / 2)
        duracion_vacio = max(0.5, mock_interval_s - duracion_animal)
        corral = _CorralSimulado(
            duracion_animal_s=duracion_animal,
            duracion_vacio_s=duracion_vacio,
            peso_min_kg=cfg.peso_min_kg,
            clock=clock,
        )
        rfid: HardwareBackend = _RfidSimuladoEstacion(corral)
        bascula: HardwareBackend = _BasculaSimuladaEstacion(corral)
        fuente: str | None = FUENTE_ESTACION_SIM
    else:
        serial = SerialHardware(scale_port=scale_port, rfid_port=rfid_port)
        rfid = serial
        bascula = serial
        fuente = None
    return EstacionHardware(
        rfid,
        bascula,
        banda_kg=cfg.estable_banda_kg,
        ventana_estable_s=cfg.estable_ventana_s,
        peso_min_kg=cfg.peso_min_kg,
        cero_kg=cfg.cero_kg,
        ventana_tag_s=cfg.ventana_tag_s,
        fuente=fuente,
        clock=clock,
    )
