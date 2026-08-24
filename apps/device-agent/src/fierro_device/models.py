from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class WeightReading:
    event_id: str
    device_id: str
    tag_id: str
    weight_kg: float
    captured_at: str
    stable: bool = True
    source: str = "mock"

    @classmethod
    def create(
        cls,
        *,
        device_id: str,
        tag_id: str,
        weight_kg: float,
        source: str = "mock",
        stable: bool = True,
        event_id: str | None = None,
        captured_at: datetime | None = None,
    ) -> WeightReading:
        ts = captured_at or utc_now()
        return cls(
            event_id=event_id or str(uuid4()),
            device_id=device_id,
            tag_id=tag_id,
            weight_kg=round(float(weight_kg), 2),
            captured_at=ts.isoformat(),
            stable=stable,
            source=source,
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
