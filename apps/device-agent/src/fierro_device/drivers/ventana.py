"""Tag capture window shared by prototype and station matching backends."""

from __future__ import annotations

import time
from collections.abc import Callable


class VentanaCaptura:
    """Tracks an open matching window for a single RFID tag."""

    def __init__(
        self,
        ventana_s: float = 5.0,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        if ventana_s <= 0:
            raise ValueError(f"ventana_s debe ser > 0, recibido {ventana_s}")
        self._ventana_s = ventana_s
        self._clock = clock
        self._tag: str | None = None
        self._desde = 0.0
        self._anulada = False

    @property
    def tag(self) -> str | None:
        return self._tag

    @property
    def abierta(self) -> bool:
        return self._tag is not None

    @property
    def anulada(self) -> bool:
        return self._anulada

    def abrir(self, tag_id: str) -> None:
        self._tag = tag_id
        self._desde = self._clock()
        self._anulada = False

    def anular(self) -> None:
        if self._tag is not None:
            self._anulada = True

    def vencida(self) -> bool:
        if self._tag is None:
            return False
        return (self._clock() - self._desde) >= self._ventana_s

    def cerrar(self) -> str | None:
        anterior = self._tag
        self._tag = None
        self._anulada = False
        return anterior
