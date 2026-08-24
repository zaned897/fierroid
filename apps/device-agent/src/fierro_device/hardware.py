from __future__ import annotations

import random
import time
from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class HardwareSample:
    tag_id: str | None
    weight_kg: float | None
    stable: bool
    source: str


class HardwareBackend(Protocol):
    def read(self) -> HardwareSample: ...


class MockHardware:
    """Simulates alley traffic: occasional RFID + stable weight pairs."""

    def __init__(self, interval_s: float = 3.0) -> None:
        self.interval_s = interval_s
        self._next_at = 0.0
        self._tags = [
            "982000111111111",
            "982000222222222",
            "982000333333333",
            "982000444444444",
        ]

    def read(self) -> HardwareSample:
        now = time.monotonic()
        if now < self._next_at:
            return HardwareSample(None, None, False, "mock")
        self._next_at = now + self.interval_s
        tag = random.choice(self._tags)
        weight = round(random.uniform(280.0, 620.0), 1)
        return HardwareSample(tag, weight, True, "mock")


class SerialHardware:
    """
    Placeholder for real RS232 scale + RFID panel.

    Wire pyserial here once indicator/reader protocols are known.
    Until then, raises to avoid silent fake data in production.
    """

    def __init__(self, scale_port: str, rfid_port: str) -> None:
        self.scale_port = scale_port
        self.rfid_port = rfid_port

    def read(self) -> HardwareSample:
        raise NotImplementedError(
            "Serial drivers not configured. Set FIERRO_MOCK_HW=1 for lab, "
            f"or implement protocol for scale={self.scale_port} rfid={self.rfid_port}"
        )


def build_hardware(
    *,
    mock: bool,
    scale_port: str,
    rfid_port: str,
    mock_interval_s: float,
) -> HardwareBackend:
    if mock:
        return MockHardware(interval_s=mock_interval_s)
    return SerialHardware(scale_port=scale_port, rfid_port=rfid_port)
