"""Weight stability filter shared by simulated and real station backends."""

from __future__ import annotations

import time
from collections.abc import Callable


class FiltroEstable:
    """Marks a weight signal stable once it holds within +/-banda_kg for ventana_s."""

    def __init__(
        self,
        banda_kg: float = 0.5,
        ventana_s: float = 1.0,
        clock: Callable[[], float] = time.monotonic,
        *,
        estable_inicial: bool = False,
    ) -> None:
        if banda_kg < 0:
            raise ValueError(f"banda_kg debe ser >= 0, recibido {banda_kg}")
        if ventana_s < 0:
            raise ValueError(f"ventana_s debe ser >= 0, recibido {ventana_s}")
        self._banda_kg = banda_kg
        self._ventana_s = ventana_s
        self._clock = clock
        self._estable_inicial = estable_inicial
        self._ancla_kg: float | None = None
        self._estable_desde = float("-inf") if estable_inicial else 0.0

    def evaluar(self, kg: float) -> bool:
        ahora = self._clock()
        ancla = self._ancla_kg
        if ancla is None:
            self._ancla_kg = kg
            if not self._estable_inicial:
                self._estable_desde = ahora
        elif abs(kg - ancla) > self._banda_kg:
            self._ancla_kg = kg
            self._estable_desde = ahora
        return (ahora - self._estable_desde) >= self._ventana_s

    def reiniciar(self) -> None:
        self._ancla_kg = None
        self._estable_desde = float("-inf") if self._estable_inicial else 0.0
