from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any


class ReadingStore:
    def __init__(self, path: str) -> None:
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL")
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
              received_at TEXT NOT NULL DEFAULT (datetime('now'))
            );
            CREATE INDEX IF NOT EXISTS idx_readings_captured ON readings(captured_at DESC);
            CREATE TABLE IF NOT EXISTS devices (
              device_id TEXT PRIMARY KEY,
              pending_count INTEGER NOT NULL DEFAULT 0,
              agent_version TEXT,
              uptime_s INTEGER,
              last_seen TEXT NOT NULL
            );
            """
        )
        self._conn.commit()

    def upsert_readings(self, readings: list[dict[str, Any]]) -> tuple[list[str], list[str]]:
        accepted: list[str] = []
        duplicates: list[str] = []
        for r in readings:
            event_id = r["event_id"]
            try:
                self._conn.execute(
                    """
                    INSERT INTO readings (
                      event_id, device_id, tag_id, weight_kg,
                      captured_at, stable, source
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        event_id,
                        r["device_id"],
                        r["tag_id"],
                        float(r["weight_kg"]),
                        r["captured_at"],
                        1 if r.get("stable", True) else 0,
                        r.get("source", "unknown"),
                    ),
                )
                accepted.append(event_id)
            except sqlite3.IntegrityError:
                duplicates.append(event_id)
                accepted.append(event_id)  # idempotent ACK
        self._conn.commit()
        return accepted, duplicates

    def list_readings(
        self,
        limit: int = 50,
        *,
        org_slug: str | None = None,  # noqa: ARG002 - ver docstring
        device_id: str | None = None,
        tag_id: str | None = None,
        cursor: tuple[str, str] | None = None,
    ) -> list[dict[str, Any]]:
        """Misma firma que el store Postgres, para que main.py no distinga.

        org_slug se ignora a proposito: el modo SQLite es el laboratorio de un
        solo inquilino y no tiene tablas de organizaciones. Implementar aqui
        una segunda version de la separacion multi-cliente seria duplicar la
        parte del sistema donde un error cuesta mas caro.
        """
        condiciones: list[str] = []
        parametros: list[Any] = []
        if device_id:
            condiciones.append("device_id = ?")
            parametros.append(device_id)
        if tag_id:
            condiciones.append("tag_id = ?")
            parametros.append(tag_id)
        if cursor:
            condiciones.append("(captured_at, event_id) < (?, ?)")
            parametros.extend(cursor)
        where = ("WHERE " + " AND ".join(condiciones)) if condiciones else ""
        parametros.append(limit)

        rows = self._conn.execute(
            f"""
            SELECT event_id, device_id, tag_id, weight_kg, captured_at,
                   stable, source, received_at
            FROM readings
            {where}
            ORDER BY captured_at DESC, event_id DESC
            LIMIT ?
            """,
            parametros,
        ).fetchall()
        return [
            {
                "event_id": row["event_id"],
                "device_id": row["device_id"],
                "tag_id": row["tag_id"],
                "weight_kg": row["weight_kg"],
                "captured_at": row["captured_at"],
                "stable": bool(row["stable"]),
                "source": row["source"],
                "received_at": row["received_at"],
            }
            for row in rows
        ]

    def heartbeat(
        self,
        device_id: str,
        *,
        pending_count: int,
        agent_version: str | None,
        uptime_s: int | None,
    ) -> None:
        self._conn.execute(
            """
            INSERT INTO devices (device_id, pending_count, agent_version, uptime_s, last_seen)
            VALUES (?, ?, ?, ?, datetime('now'))
            ON CONFLICT(device_id) DO UPDATE SET
              pending_count = excluded.pending_count,
              agent_version = excluded.agent_version,
              uptime_s = excluded.uptime_s,
              last_seen = excluded.last_seen
            """,
            (device_id, pending_count, agent_version, uptime_s),
        )
        self._conn.commit()

    def list_devices(self, *, org_slug: str | None = None) -> list[dict[str, Any]]:  # noqa: ARG002
        """org_slug se ignora: SQLite es de un solo inquilino. Ver list_readings."""
        rows = self._conn.execute(
            """
            SELECT device_id, pending_count, agent_version, uptime_s, last_seen
            FROM devices
            ORDER BY last_seen DESC
            """
        ).fetchall()
        return [dict(row) for row in rows]


def build_store(*, dsn: str | None, db_path: str) -> Any:
    """SQLite para laboratorio, Postgres cuando hay DSN.

    El import de psycopg es perezoso: `pip install fierro-api` sin el extra
    [postgres] sigue levantando la API en SQLite.
    """
    if dsn:
        from fierro_api.store_pg import PostgresReadingStore

        return PostgresReadingStore(dsn)
    return ReadingStore(db_path)
