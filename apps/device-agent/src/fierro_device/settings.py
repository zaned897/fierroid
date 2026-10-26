from __future__ import annotations

import os
from dataclasses import dataclass

from fierro_device.config import default_db_path


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
