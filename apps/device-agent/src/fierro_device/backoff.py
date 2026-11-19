"""Backoff exponencial con jitter para el sync, y su estado para `doctor`.

Con miles de estaciones que recuperan la red a la vez, reintentar a ritmo fijo es
una estampida contra la API. El intervalo se duplica en cada fallo hasta un tope y
vuelve al minimo con el primer exito. El jitter reparte los reintentos.
"""

from __future__ import annotations

import json
import os
import random
from collections.abc import Callable
from pathlib import Path
from typing import Any


class Backoff:
    def __init__(
        self,
        minimo_s: float,
        maximo_s: float,
        aleatorio: Callable[[], float] = random.random,
    ) -> None:
        self.minimo_s = max(minimo_s, 0.0)
        self.maximo_s = max(maximo_s, self.minimo_s)
        self.intervalo_s = self.minimo_s
        self._aleatorio = aleatorio

    def exito(self) -> None:
        self.intervalo_s = self.minimo_s

    def fallo(self) -> None:
        self.intervalo_s = min(max(self.intervalo_s, 0.5) * 2, self.maximo_s)

    def espera(self) -> float:
        """Siguiente espera: entre la mitad y el intervalo completo (equal jitter)."""
        mitad = self.intervalo_s / 2
        return mitad + mitad * self._aleatorio()


def ruta_estado(db_path: str) -> Path:
    """Archivo de estado del sync, junto a la outbox (sin tabla nueva)."""
    return Path(f"{db_path}.sync.json")


def guardar_estado(db_path: str, estado: dict[str, Any]) -> None:
    """Escritura atomica; se llama solo cuando el estado cambia (desgaste de la SD)."""
    ruta = ruta_estado(db_path)
    tmp = ruta.with_suffix(".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(json.dumps(estado))
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, ruta)


def leer_estado(db_path: str) -> dict[str, Any] | None:
    try:
        datos = json.loads(ruta_estado(db_path).read_text())
    except (OSError, ValueError):
        return None
    return datos if isinstance(datos, dict) else None
