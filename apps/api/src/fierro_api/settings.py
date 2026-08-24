from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    db_path: str
    host: str
    port: int

    @classmethod
    def from_env(cls) -> Settings:
        return cls(
            db_path=os.getenv("FIERRO_API_DB_PATH", "/tmp/fierro-api.db"),
            host=os.getenv("FIERRO_API_HOST", "0.0.0.0"),
            port=int(os.getenv("FIERRO_API_PORT", "8000")),
        )
