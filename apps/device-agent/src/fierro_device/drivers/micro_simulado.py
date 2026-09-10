"""Virtual micro: a transport that speaks ard_com_test.ino's line protocol.

It exists so the driver, the agent and the platform can be exercised with no
hardware on the bench. It replays what the bench showed: the DTR reset banner
on open, link heartbeats, and one W line per presentar() call. Everything it
produces ends up labeled proto-sim upstream — never pretend it is hardware.

This module is meant to be deleted when the bench is permanent hardware; it
lives apart for exactly that reason.
"""

from __future__ import annotations

import random
import time
from collections.abc import Callable

BANNER_MICRO = (
    b"== Fierro proto \xe2\x80\x94 pesaje por evento ==\r\n"
    b"lineas: W,<uid>,<adc> | H,<millis> | # diagnostico\r\n"
    b"RC522 version: 0x92\r\n"
    b"cfg estable_ms=800\r\n"
    b"cfg banda_adc=8\r\n"
    b"cfg timeout_ms=8000\r\n"
    b"cfg ausencia_ms=400\r\n"
    b"cfg heartbeat_ms=10000\r\n"
    b"Listo. Presenta una tarjeta...\r\n"
)

UIDS_AUTO = ("04A3B1C2", "05D4E3F2", "04B7C8D9", "05E1F2A3")


class MicroSimulado:
    """TransporteSerie implementation: bytes in, W/H/# lines out."""

    def __init__(
        self,
        *,
        heartbeats: bool = True,
        intervalo_heartbeat_s: float = 10.0,
        auto_intervalo_s: float = 0.0,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._cola = bytearray()
        self._heartbeats = heartbeats
        self._intervalo = intervalo_heartbeat_s
        self._auto_intervalo = auto_intervalo_s
        self._clock = clock
        self._inicio = clock()
        self._ultimo_heartbeat = float("-inf")
        self._ultimo_auto = float("-inf")
        self._abierto = False

    def abrir(self) -> None:
        self._cola.extend(BANNER_MICRO)
        self._inicio = self._clock()
        self._abierto = True

    def cerrar(self) -> None:
        self._abierto = False

    def presentar(
        self, uid: str, adc: int, *, estable: bool = True
    ) -> None:
        if not self._abierto:
            raise RuntimeError("micro simulado no abierto")
        self._cola.extend(f"W,{uid},{adc}\r\n".encode("ascii"))
        if not estable:
            self._cola.extend(b"# emitido por timeout: no estabilizo\r\n")

    def leer(self, n: int) -> bytes:
        if not self._abierto:
            raise RuntimeError("micro simulado no abierto")
        self._latido_si_toca()
        self._auto_si_toca()
        salida = bytes(self._cola[:n])
        del self._cola[:n]
        return salida

    def _latido_si_toca(self) -> None:
        if not self._heartbeats:
            return
        ahora = self._clock()
        if ahora - self._ultimo_heartbeat < self._intervalo:
            return
        self._ultimo_heartbeat = ahora
        millis = int((ahora - self._inicio) * 1000)
        self._cola.extend(f"H,{millis}\r\n".encode("ascii"))

    def _auto_si_toca(self) -> None:
        if self._auto_intervalo <= 0:
            return
        ahora = self._clock()
        if ahora - self._ultimo_auto < self._auto_intervalo:
            return
        self._ultimo_auto = ahora
        self.presentar(random.choice(UIDS_AUTO), random.randint(150, 950))
