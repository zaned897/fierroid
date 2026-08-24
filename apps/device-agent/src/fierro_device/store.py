from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

from fierro_device.models import WeightReading


class OutboxStore:
    """Durable local store: capture success == row committed here."""

    def __init__(self, path: str) -> None:
        self.path = path
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA synchronous=NORMAL")
        self._migrate()

    def _migrate(self) -> None:
        self._conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS readings (
              event_id TEXT PRIMARY KEY,
              device_id TEXT NOT NULL,
              tag_id TEXT NOT NULL,
              weight_kg REAL NOT NULL,
              captured_at TEXT NOT NULL,
              stable INTEGER NOT NULL,
              source TEXT NOT NULL,
              payload TEXT NOT NULL,
              status TEXT NOT NULL DEFAULT 'pending',
              created_at TEXT NOT NULL DEFAULT (datetime('now')),
              synced_at TEXT
            );
            CREATE INDEX IF NOT EXISTS idx_readings_status ON readings(status);
            """
        )
        self._conn.commit()

    def save_reading(self, reading: WeightReading) -> bool:
        """Insert reading. Returns False if event_id already exists."""
        payload = json.dumps(reading.to_dict())
        try:
            self._conn.execute(
                """
                INSERT INTO readings (
                  event_id, device_id, tag_id, weight_kg, captured_at,
                  stable, source, payload, status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'pending')
                """,
                (
                    reading.event_id,
                    reading.device_id,
                    reading.tag_id,
                    reading.weight_kg,
                    reading.captured_at,
                    1 if reading.stable else 0,
                    reading.source,
                    payload,
                ),
            )
            self._conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False

    def pending(self, limit: int = 50) -> list[dict[str, Any]]:
        rows = self._conn.execute(
            """
            SELECT payload FROM readings
            WHERE status = 'pending'
            ORDER BY created_at ASC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
        return [json.loads(r["payload"]) for r in rows]

    def mark_synced(self, event_ids: list[str]) -> None:
        if not event_ids:
            return
        placeholders = ",".join("?" for _ in event_ids)
        self._conn.execute(
            f"""
            UPDATE readings
            SET status = 'synced', synced_at = datetime('now')
            WHERE event_id IN ({placeholders})
            """,
            event_ids,
        )
        self._conn.commit()

    def pending_count(self) -> int:
        row = self._conn.execute(
            "SELECT COUNT(*) AS c FROM readings WHERE status = 'pending'"
        ).fetchone()
        return int(row["c"])

    def close(self) -> None:
        self._conn.close()
