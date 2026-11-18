"""Diario de la organización; autor del servidor y reintentos idempotentes."""

from datetime import datetime
from typing import Any
from uuid import UUID

from fierro_api.animals import _org_id

# La misma proyección sirve al confirmar una escritura y al consultar el diario.
_ENTRY_SELECT = """
    SELECT j.*, COALESCE(NULLIF(u.full_name,''), u.email, 'Notas de la ficha') AS author,
           ARRAY(
             SELECT a.tag_id FROM journal_entry_animals ea
             JOIN animals a ON a.id=ea.animal_id AND a.org_id=ea.org_id
             WHERE ea.entry_id=j.entry_id AND ea.org_id=j.org_id ORDER BY a.tag_id
           ) AS tags
    FROM journal_entries j
    JOIN organizations o ON o.id=j.org_id LEFT JOIN users u ON u.id=j.author_id
"""


class EntryConflict(ValueError):
    """La clave de reintento ya representa otra anotación."""


def _public(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "entry_id": str(row["entry_id"]),
        "occurred_at": row["occurred_at"].isoformat(),
        "created_at": row["created_at"].isoformat(),
        "category": row["category"], "body": row["body"],
        "author": row["author"], "tags": row["tags"], "source": row["source"],
    }


def add_ranch_entry(
    dsn: str, *, org: str, tags: list[str], author_id: int, entry_id: UUID,
    occurred_at: datetime, category: str, body: str,
) -> dict[str, Any]:
    import psycopg
    from psycopg.rows import dict_row

    tags = sorted(set(tags))
    with psycopg.connect(dsn, row_factory=dict_row) as conn, conn.cursor() as cur:
        org_id = _org_id(cur, org)
        cur.execute(
            "INSERT INTO journal_entries"
            "(entry_id, org_id, author_id, occurred_at, category, body) "
            "VALUES (%s,%s,%s,%s,%s,%s) ON CONFLICT (entry_id) DO NOTHING",
            (entry_id, org_id, author_id, occurred_at, category, body),
        )
        if cur.rowcount:
            # Orden estable: dos lotes con animales compartidos no toman locks al revés.
            for tag in tags:
                cur.execute(
                    "INSERT INTO animals(org_id, tag_id) VALUES (%s, %s) "
                    "ON CONFLICT (org_id, tag_id) DO NOTHING", (org_id, tag),
                )
                cur.execute(
                    "INSERT INTO journal_entry_animals(entry_id, animal_id, org_id) "
                    "SELECT %s, id, org_id FROM animals WHERE org_id=%s AND tag_id=%s",
                    (entry_id, org_id, tag),
                )
        # ON CONFLICT espera al primer commit, incluidos todos sus vínculos.
        cur.execute(_ENTRY_SELECT + " WHERE j.entry_id=%s", (entry_id,))
        row = cur.fetchone()
        if row is None:
            raise RuntimeError("No se pudo confirmar la anotación")
        if any(row[key] != value for key, value in {
            "org_id": org_id, "tags": tags, "author_id": author_id, "occurred_at": occurred_at,
            "category": category, "body": body, "source": "diario",
        }.items()):
            raise EntryConflict("La clave ya corresponde a otra anotación.")
        return _public(row)


def add_entry(
    dsn: str, *, org: str, tag: str, author_id: int, entry_id: UUID,
    occurred_at: datetime, category: str, body: str,
) -> dict[str, Any]:
    """Compatibilidad con la bitácora de una ficha."""
    return add_ranch_entry(
        dsn, org=org, tags=[tag], author_id=author_id, entry_id=entry_id,
        occurred_at=occurred_at, category=category, body=body,
    )


def list_entries(
    dsn: str, *, org: str, limit: int, tag: str | None = None,
    before: tuple[datetime, UUID] | None = None,
    desde: datetime | None = None, hasta: datetime | None = None,
) -> list[dict[str, Any]]:
    import psycopg
    from psycopg.rows import dict_row

    params: list[Any] = [org]
    condition = " WHERE o.slug=%s"
    if tag is not None:
        condition += (
            " AND EXISTS (SELECT 1 FROM journal_entry_animals ea "
            "JOIN animals a ON a.id=ea.animal_id AND a.org_id=ea.org_id "
            "WHERE ea.entry_id=j.entry_id AND ea.org_id=j.org_id AND a.tag_id=%s)"
        )
        params.append(tag)
    if desde is not None:
        condition += " AND j.occurred_at >= %s"
        params.append(desde)
    if hasta is not None:
        condition += " AND j.occurred_at < %s"
        params.append(hasta)
    if before:
        condition += " AND (j.occurred_at, j.entry_id) < (%s, %s)"
        params.extend(before)
    params.append(limit)
    with psycopg.connect(dsn, row_factory=dict_row) as conn, conn.cursor() as cur:
        cur.execute(
            _ENTRY_SELECT + condition +
            " ORDER BY j.occurred_at DESC, j.entry_id DESC LIMIT %s", params,
        )
        return [_public(row) for row in cur.fetchall()]
