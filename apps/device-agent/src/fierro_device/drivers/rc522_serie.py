"""Driver of the prototype RFID reader (ticket #46).

The micro (ard_com_test.ino) owns signal conditioning: a tag opens a session,
the weight is emitted exactly once per session, either stabilized or by
timeout. Lines over USB-CDC at 115200 8N1, CRLF:

    W,<uid-hex>,<adc 0-1023>   complete weighing, tag and weight paired
    H,<millis>                 link heartbeat, not data
    # ...                      human diagnostics, ignorable

Findings from the bench (hardware/test-fixtures/rfid-mfrc522/README.md):
opening the port resets the Arduino via DTR, so a banner + cfg block arrives
before data; serial chunks do not always carry whole lines.

Boundary rules: this driver only knows the line protocol. Conversions to kg,
the proto: prefix on tags and the source label happen here; event_id, business
rules and the cloud live upstream. The transport is injected, so the same
parser runs against a real COM port or the virtual micro in tests and CI.
"""

from __future__ import annotations

import logging
from typing import Any, Protocol

from fierro_device.drivers.peso_simulado import cuantizar_kg, mapear_adc_a_kg
from fierro_device.hardware import HardwareSample

logger = logging.getLogger("fierro_device")

FUENTE_RC522 = "proto-rc522"
PREFIJO_TAG = "proto:"
BAUDIOS_RC522 = 115200
RANGO_KG_RC522: tuple[float, float] = (30.0, 900.0)
MARCADOR_TIMEOUT = "# emitido por timeout"


class TransporteSerie(Protocol):
    def abrir(self) -> None: ...
    def leer(self, n: int) -> bytes: ...
    def cerrar(self) -> None: ...


class PuertoSerie:
    """Real transport over pyserial. Opens lazily and fails loudly."""

    def __init__(self, puerto: str, baudios: int = BAUDIOS_RC522) -> None:
        self._puerto = puerto
        self._baudios = baudios
        self._serie: Any = None

    def abrir(self) -> None:
        import serial

        self._serie = serial.Serial(self._puerto, self._baudios, timeout=0.2)
        logger.info("puerto %s abierto a %d 8N1", self._puerto, self._baudios)

    def leer(self, n: int) -> bytes:
        if self._serie is None:
            raise RuntimeError("puerto no abierto")
        try:
            return bytes(self._serie.read(n))
        except Exception:
            self.cerrar()
            raise

    def cerrar(self) -> None:
        if self._serie is not None:
            self._serie.close()
            self._serie = None


class Rc522Serie:
    """HardwareBackend over the micro's W/H/# line protocol."""

    def __init__(
        self,
        transporte: TransporteSerie,
        *,
        fuente: str = FUENTE_RC522,
        rango_kg: tuple[float, float] = RANGO_KG_RC522,
    ) -> None:
        self._transporte = transporte
        self._fuente = fuente
        self._rango_kg = rango_kg
        self._abierto = False
        self._buffer = bytearray()
        self._banner_pendiente = True
        self._pendiente: HardwareSample | None = None
        self._confirmadas: list[HardwareSample] = []
        self.eventos = 0
        self.latidos = 0
        self.lineas_descartadas = 0

    def read(self) -> HardwareSample:
        try:
            self._asegurar_abierto()
            self._bombeo()
        except Exception:
            self.close()
            raise
        # El micro emite el comentario de timeout en el mismo burst que su W,
        # asi que un W que sobrevive a un bombeo completo quedo estabilizado.
        self._resolver_pendiente(estable=True)
        if self._confirmadas:
            return self._confirmadas.pop(0)
        return HardwareSample(None, None, False, self._fuente)

    def close(self) -> None:
        if self._abierto:
            self._transporte.cerrar()
            self._abierto = False

    def _asegurar_abierto(self) -> None:
        if not self._abierto:
            self._transporte.abrir()
            self._abierto = True

    def _bombeo(self) -> None:
        while True:
            datos = self._transporte.leer(4096)
            if not datos:
                break
            self._buffer.extend(datos)
            while True:
                fin = self._buffer.find(b"\n")
                if fin < 0:
                    break
                linea = bytes(self._buffer[:fin]).decode("utf-8", "replace").strip()
                del self._buffer[: fin + 1]
                if linea:
                    self._linea(linea)

    def _linea(self, linea: str) -> None:
        if self._banner_pendiente:
            if linea.startswith(("W,", "H,", "#")):
                self._banner_pendiente = False
            elif linea.startswith("Listo."):
                self._banner_pendiente = False
                return
            else:
                self.lineas_descartadas += 1
                return
        if linea.startswith("#"):
            if MARCADOR_TIMEOUT in linea:
                self._resolver_pendiente(estable=False)
            return
        self._resolver_pendiente(estable=True)
        if linea.startswith("W,"):
            partes = linea.split(",")
            if len(partes) != 3 or not partes[2].isdigit():
                self.lineas_descartadas += 1
                return
            self.eventos += 1
            self._pendiente = HardwareSample(
                tag_id=PREFIJO_TAG + partes[1],
                weight_kg=cuantizar_kg(mapear_adc_a_kg(int(partes[2]), self._rango_kg)),
                stable=True,
                source=self._fuente,
            )
        elif linea.startswith("H,"):
            self.latidos += 1
        else:
            self.lineas_descartadas += 1
            logger.warning("linea desconocida del micro: %r", linea)

    def _resolver_pendiente(self, *, estable: bool) -> None:
        pendiente = self._pendiente
        if pendiente is None:
            return
        self._confirmadas.append(
            HardwareSample(
                tag_id=pendiente.tag_id,
                weight_kg=pendiente.weight_kg,
                stable=estable,
                source=pendiente.source,
            )
        )
        self._pendiente = None
