from __future__ import annotations

import os
from dataclasses import dataclass

from fierro_device.config import default_db_path

# Parametros de emparejamiento de estacion (valores por defecto para ganado bovino):
# - FIERRO_ESTABLE_BANDA_KG: tolerancia +/- kg para considerar el peso quieto.
# - FIERRO_ESTABLE_VENTANA_S: segundos continuos dentro de la banda de estabilidad.
# - FIERRO_PESO_MIN_KG: peso minimo de animal (evita emitir perros u objetos).
# - FIERRO_CERO_KG: umbral bajo el cual la plataforma queda vacia y rearma.
# - FIERRO_VENTANA_TAG_S: segundos maximos para emparejar un arete con peso estable.
DEFAULT_ESTABLE_BANDA_KG = 0.5
DEFAULT_ESTABLE_VENTANA_S = 1.0
DEFAULT_PESO_MIN_KG = 30.0
DEFAULT_CERO_KG = 20.0
DEFAULT_VENTANA_TAG_S = 5.0


@dataclass(frozen=True)
class Settings:
    device_id: str
    db_path: str
    api_url: str
    mock_hw: bool
    poll_interval_s: float
    sync_interval_s: float
    mock_interval_s: float
    scale_port: str
    rfid_port: str
    estable_banda_kg: float = DEFAULT_ESTABLE_BANDA_KG
    estable_ventana_s: float = DEFAULT_ESTABLE_VENTANA_S
    peso_min_kg: float = DEFAULT_PESO_MIN_KG
    cero_kg: float = DEFAULT_CERO_KG
    ventana_tag_s: float = DEFAULT_VENTANA_TAG_S

    @classmethod
    def from_env(cls) -> Settings:
        return cls(
            device_id=os.getenv("FIERRO_DEVICE_ID", "rpi-dev-001"),
            db_path=os.getenv("FIERRO_DB_PATH") or str(default_db_path()),
            api_url=os.getenv("FIERRO_API_URL", "http://127.0.0.1:8000").rstrip("/"),
            # Hardware real por defecto: simular exige pedirlo explicitamente.
            mock_hw=os.getenv("FIERRO_MOCK_HW", "0") == "1",
            poll_interval_s=float(os.getenv("FIERRO_POLL_INTERVAL_S", "0.5")),
            sync_interval_s=float(os.getenv("FIERRO_SYNC_INTERVAL_S", "2.0")),
            mock_interval_s=float(os.getenv("FIERRO_MOCK_INTERVAL_S", "3.0")),
            scale_port=os.getenv("FIERRO_SCALE_PORT", "/dev/ttyUSB0"),
            rfid_port=os.getenv("FIERRO_RFID_PORT", "/dev/ttyUSB1"),
            estable_banda_kg=float(
                os.getenv("FIERRO_ESTABLE_BANDA_KG", str(DEFAULT_ESTABLE_BANDA_KG))
            ),
            estable_ventana_s=float(
                os.getenv("FIERRO_ESTABLE_VENTANA_S", str(DEFAULT_ESTABLE_VENTANA_S))
            ),
            peso_min_kg=float(os.getenv("FIERRO_PESO_MIN_KG", str(DEFAULT_PESO_MIN_KG))),
            cero_kg=float(os.getenv("FIERRO_CERO_KG", str(DEFAULT_CERO_KG))),
            ventana_tag_s=float(os.getenv("FIERRO_VENTANA_TAG_S", str(DEFAULT_VENTANA_TAG_S))),
        )

    def problems(self) -> list[str]:
        """Configuracion que no debe llegar a capturar con hardware real."""
        if self.mock_hw:
            return []
        faltan = [
            nombre
            for nombre in ("FIERRO_DEVICE_ID", "FIERRO_API_URL")
            if not os.getenv(nombre)
        ]
        return [f"falta {nombre} (hardware real requiere configurarlo)" for nombre in faltan]
