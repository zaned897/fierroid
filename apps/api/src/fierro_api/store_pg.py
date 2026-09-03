"""Store de la API respaldado por Postgres.

Misma interfaz que ReadingStore (SQLite) para que main.py no sepa cual usa.
SQLite sigue siendo el default de laboratorio; Postgres es el destino de
produccion (ticket E2-S1).
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool


def _as_utc(value: str | datetime) -> datetime:
    dt = value if isinstance(value, datetime) else datetime.fromisoformat(value)
    if dt.tzinfo is None:
        # Un timestamp sin zona es ambiguo. El contrato dice UTC (ISO-8601).
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def _iso(value: datetime | None) -> str | None:
    return value.isoformat() if value is not None else None


class PostgresReadingStore:
    def __init__(self, dsn: str, *, min_size: int = 1, max_size: int = 10) -> None:
        self._pool = ConnectionPool(
            dsn,
            min_size=min_size,
            max_size=max_size,
            kwargs={"row_factory": dict_row},
            open=True,
        )

    def upsert_readings(self, readings: list[dict[str, Any]]) -> tuple[list[str], list[str]]:
        """Ingest idempotente. Devuelve (accepted_ids, duplicate_ids).

        Un duplicado tambien va en accepted: el device ya hizo su trabajo y
        debe poder marcar la fila como synced.
        """
        if not readings:
            return [], []

        columns = list(
            zip(
                *[
                    (
                        r["event_id"],
                        r["device_id"],
                        r["tag_id"],
                        float(r["weight_kg"]),
                        _as_utc(r["captured_at"]),
                        bool(r.get("stable", True)),
                        r.get("source", "unknown"),
                    )
                    for r in readings
                ],
                strict=True,
            )
        )

        with self._pool.connection() as conn, conn.cursor() as cur:
            # unnest: un solo round trip para todo el lote, no uno por lectura.
            # A miles de estaciones la diferencia deja de ser cosmetica.
            cur.execute(
                """
                INSERT INTO readings (
                  event_id, device_id, tag_id, weight_kg, captured_at, stable, source
                )
                SELECT * FROM unnest(
                  %s::text[], %s::text[], %s::text[], %s::float8[],
                  %s::timestamptz[], %s::bool[], %s::text[]
                )
                ON CONFLICT (event_id) DO NOTHING
                RETURNING event_id
                """,
                [list(col) for col in columns],
            )
            inserted = {row["event_id"] for row in cur.fetchall()}

        accepted: list[str] = []
        duplicates: list[str] = []
        seen: set[str] = set()
        for r in readings:
            event_id = r["event_id"]
            accepted.append(event_id)
            if event_id not in inserted or event_id in seen:
                duplicates.append(event_id)
            seen.add(event_id)
        return accepted, duplicates

    def list_readings(
        self,
        limit: int = 50,
        *,
        org_slug: str | None = None,
        device_id: str | None = None,
        tag_id: str | None = None,
        cursor: tuple[str, str] | None = None,
    ) -> list[dict[str, Any]]:
        """Lecturas mas recientes primero.

        org_slug=None significa "sin restringir" y solo lo usa un superusuario.
        Un usuario normal SIEMPRE llega aqui con su organizacion.

        Las estaciones sin rancho asignado no pertenecen a nadie todavia, asi
        que no aparecen bajo ninguna organizacion: sus lecturas se guardan
        igual, pero no se le muestran a un inquilino que no es su dueno.
        """
        condiciones: list[str] = []
        parametros: list[Any] = []

        if org_slug is not None:
            condiciones.append(
                "d.ranch_id IS NOT NULL AND o.slug = %s"
            )
            parametros.append(org_slug)
        if device_id:
            condiciones.append("r.device_id = %s")
            parametros.append(device_id)
        if tag_id:
            condiciones.append("r.tag_id = %s")
            parametros.append(tag_id)
        if cursor:
            # Paginacion por (captured_at, event_id): captured_at solo no basta
            # porque dos lecturas pueden compartir el mismo instante y una se
            # perderia entre paginas.
            condiciones.append("(r.captured_at, r.event_id) < (%s, %s)")
            parametros.extend(cursor)

        where = ("WHERE " + " AND ".join(condiciones)) if condiciones else ""
        parametros.append(limit)

        with self._pool.connection() as conn, conn.cursor() as cur:
            cur.execute(
                f"""
                SELECT r.event_id, r.device_id, r.tag_id, r.weight_kg, r.captured_at,
                       r.stable, r.source, r.received_at
                FROM readings r
                LEFT JOIN devices d ON d.device_id = r.device_id
                LEFT JOIN ranches ra ON ra.id = d.ranch_id
                LEFT JOIN organizations o ON o.id = ra.org_id
                {where}
                ORDER BY r.captured_at DESC, r.event_id DESC
                LIMIT %s
                """,
                parametros,
            )
            rows = cur.fetchall()

        return [
            {
                "event_id": row["event_id"],
                "device_id": row["device_id"],
                "tag_id": row["tag_id"],
                "weight_kg": row["weight_kg"],
                "captured_at": _iso(row["captured_at"]),
                "stable": bool(row["stable"]),
                "source": row["source"],
                "received_at": _iso(row["received_at"]),
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
        with self._pool.connection() as conn, conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO devices (device_id, pending_count, agent_version, uptime_s, last_seen)
                VALUES (%s, %s, %s, %s, now())
                ON CONFLICT (device_id) DO UPDATE SET
                  pending_count = EXCLUDED.pending_count,
                  agent_version = EXCLUDED.agent_version,
                  uptime_s      = EXCLUDED.uptime_s,
                  last_seen     = EXCLUDED.last_seen
                """,
                (device_id, pending_count, agent_version, uptime_s),
            )

    def list_devices(self, *, org_slug: str | None = None) -> list[dict[str, Any]]:
        """Estaciones visibles. org_slug=None solo para superusuario."""
        where = ""
        parametros: list[Any] = []
        if org_slug is not None:
            where = "WHERE d.ranch_id IS NOT NULL AND o.slug = %s"
            parametros.append(org_slug)

        with self._pool.connection() as conn, conn.cursor() as cur:
            cur.execute(
                f"""
                SELECT d.device_id, d.pending_count, d.agent_version,
                       d.uptime_s, d.last_seen
                FROM devices d
                LEFT JOIN ranches ra ON ra.id = d.ranch_id
                LEFT JOIN organizations o ON o.id = ra.org_id
                {where}
                ORDER BY d.last_seen DESC
                """,
                parametros,
            )
            rows = cur.fetchall()
        return [{**row, "last_seen": _iso(row["last_seen"])} for row in rows]

    def close(self) -> None:
        self._pool.close()
