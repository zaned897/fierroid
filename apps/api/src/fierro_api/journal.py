"""Bitácora por ficha; autor del servidor y reintentos idempotentes."""

from datetime import datetime
from typing import Any
from uuid import UUID

from fierro_api.animals import _org_id


class EntryConflict(ValueError):
    """La clave de reintento ya representa otra anotación."""


def _public(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "entry_id": str(row["entry_id"]),
        "occurred_at": row["occurred_at"].isoformat(),
        "created_at": row["created_at"].isoformat(),
        "category": row["category"], "body": row["body"],
        "author": row["author"],
    }


def add_entry(
    dsn: str, *, org: str, tag: str, author_id: int, entry_id: UUID,
    occurred_at: datetime, category: str, body: str,
) -> dict[str, Any]:
    import psycopg
    from psycopg.rows import dict_row

    with psycopg.connect(dsn, row_factory=dict_row) as conn, conn.cursor() as cur:
        org_id = _org_id(cur, org)
        cur.execute(
            "INSERT INTO animals(org_id, tag_id) VALUES (%s, %s) "
            "ON CONFLICT (org_id, tag_id) DO NOTHING", (org_id, tag),
        )
        cur.execute("SELECT id FROM animals WHERE org_id=%s AND tag_id=%s", (org_id, tag))
        animal_id = cur.fetchone()["id"]
        cur.execute(
            "INSERT INTO animal_journal"
            "(entry_id, animal_id, author_id, occurred_at, category, body) "
            "VALUES (%s,%s,%s,%s,%s,%s) ON CONFLICT (entry_id) DO NOTHING",
            (entry_id, animal_id, author_id, occurred_at, category, body),
        )
        cur.execute(
            "SELECT j.*, COALESCE(NULLIF(u.full_name,''), u.email) AS author "
            "FROM animal_journal j JOIN users u ON u.id=j.author_id WHERE j.entry_id=%s",
            (entry_id,),
        )
        row = cur.fetchone()
        if any(row[key] != value for key, value in {
            "animal_id": animal_id, "author_id": author_id, "occurred_at": occurred_at,
            "category": category, "body": body,
        }.items()):
            raise EntryConflict("La clave ya corresponde a otra anotación.")
        return _public(row)


def list_entries(
    dsn: str, *, org: str, tag: str, limit: int,
    before: tuple[datetime, UUID] | None = None,
) -> list[dict[str, Any]]:
    import psycopg
    from psycopg.rows import dict_row

    params: list[Any] = [org, tag]
    condition = ""
    if before:
        condition = " AND (j.occurred_at, j.entry_id) < (%s, %s)"
        params.extend(before)
    params.append(limit)
    with psycopg.connect(dsn, row_factory=dict_row) as conn, conn.cursor() as cur:
        cur.execute(
            "SELECT j.*, COALESCE(NULLIF(u.full_name,''), u.email) AS author "
            "FROM animal_journal j JOIN animals a ON a.id=j.animal_id "
            "JOIN organizations o ON o.id=a.org_id JOIN users u ON u.id=j.author_id "
            "WHERE o.slug=%s AND a.tag_id=%s" + condition +
            " ORDER BY j.occurred_at DESC, j.entry_id DESC LIMIT %s", params,
        )
        return [_public(row) for row in cur.fetchall()]
