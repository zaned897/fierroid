from __future__ import annotations

import os
from dataclasses import dataclass


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
            db_path=os.getenv("FIERRO_DB_PATH", "/tmp/fierro-device.db"),
            api_url=os.getenv("FIERRO_API_URL", "http://127.0.0.1:8000").rstrip("/"),
            mock_hw=os.getenv("FIERRO_MOCK_HW", "1") == "1",
            poll_interval_s=float(os.getenv("FIERRO_POLL_INTERVAL_S", "0.5")),
            sync_interval_s=float(os.getenv("FIERRO_SYNC_INTERVAL_S", "2.0")),
            mock_interval_s=float(os.getenv("FIERRO_MOCK_INTERVAL_S", "3.0")),
            scale_port=os.getenv("FIERRO_SCALE_PORT", "/dev/ttyUSB0"),
            rfid_port=os.getenv("FIERRO_RFID_PORT", "/dev/ttyUSB1"),
        )
