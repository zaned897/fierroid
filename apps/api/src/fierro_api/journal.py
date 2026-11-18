"""Diario del rancho; autor del servidor y reintentos idempotentes."""

from datetime import datetime
from typing import Any
from uuid import UUID

from fierro_api.animals import _org_id


class EntryConflict(ValueError):
    """La clave de reintento ya representa otra anotación."""


# La subconsulta evita multiplicar entradas al filtrar o paginar varios animales.
_ENTRY_SELECT = """
SELECT j.*, COALESCE(NULLIF(u.full_name,''), u.email) AS author,
       ARRAY(SELECT a.tag_id FROM journal_entry_animals ja
             JOIN animals a ON a.id=ja.animal_id AND a.org_id=ja.org_id
             WHERE ja.entry_id=j.entry_id AND ja.org_id=j.org_id
             ORDER BY a.tag_id COLLATE "C") AS tags
FROM journal_entries j LEFT JOIN users u ON u.id=j.author_id
"""


def _public(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "entry_id": str(row["entry_id"]),
        "occurred_at": row["occurred_at"].isoformat(),
        "created_at": row["created_at"].isoformat(),
        "category": row["category"], "body": row["body"],
        "author": row["author"], "tags": row["tags"], "source": row["source"],
    }


def add_entry(
    dsn: str, *, org: str, author_id: int, entry_id: UUID,
    occurred_at: datetime, category: str, body: str,
    tag: str | None = None, tags: list[str] | None = None,
) -> dict[str, Any]:
    import psycopg
    from psycopg.rows import dict_row

    animal_tags = sorted(set(tags or []) | ({tag} if tag is not None else set()))
    with psycopg.connect(dsn, row_factory=dict_row) as conn, conn.cursor() as cur:
        org_id = _org_id(cur, org)
        cur.execute(
            "INSERT INTO journal_entries"
            "(entry_id, org_id, author_id, occurred_at, category, body) "
            "VALUES (%s,%s,%s,%s,%s,%s) ON CONFLICT (entry_id) DO NOTHING "
            "RETURNING entry_id",
            (entry_id, org_id, author_id, occurred_at, category, body),
        )
        if cur.fetchone() is not None:
            # Orden estable para no bloquearse entre escrituras de varios animales.
            for animal_tag in animal_tags:
                cur.execute(
                    "INSERT INTO animals(org_id, tag_id) VALUES (%s, %s) "
                    "ON CONFLICT (org_id, tag_id) DO NOTHING", (org_id, animal_tag),
                )
                cur.execute(
                    "INSERT INTO journal_entry_animals(entry_id, animal_id, org_id) "
                    "SELECT %s, id, org_id FROM animals WHERE org_id=%s AND tag_id=%s",
                    (entry_id, org_id, animal_tag),
                )
        cur.execute(_ENTRY_SELECT + " WHERE j.entry_id=%s AND j.org_id=%s", (entry_id, org_id))
        row = cur.fetchone()
        if row is None or any(row[key] != value for key, value in {
            "author_id": author_id, "occurred_at": occurred_at,
            "category": category, "body": body, "tags": animal_tags, "source": "diario",
        }.items()):
            raise EntryConflict("La clave ya corresponde a otra anotación.")
        return _public(row)


def list_entries(
    dsn: str, *, org: str, limit: int, tag: str | None = None,
    before: tuple[datetime, UUID] | None = None,
    desde: datetime | None = None, hasta: datetime | None = None,
) -> list[dict[str, Any]]:
    import psycopg
    from psycopg.rows import dict_row

    params: list[Any] = [org]
    condition = ""
    if tag is not None:
        condition += (
            " AND EXISTS (SELECT 1 FROM journal_entry_animals ja "
            "JOIN animals a ON a.id=ja.animal_id AND a.org_id=ja.org_id "
            "WHERE ja.entry_id=j.entry_id AND ja.org_id=j.org_id AND a.tag_id=%s)"
        )
        params.append(tag)
    if desde is not None:
        condition += " AND j.occurred_at >= %s"
        params.append(desde)
    if hasta is not None:
        condition += " AND j.occurred_at <= %s"
        params.append(hasta)
    if before:
        condition += " AND (j.occurred_at, j.entry_id) < (%s, %s)"
        params.extend(before)
    params.append(limit)
    with psycopg.connect(dsn, row_factory=dict_row) as conn, conn.cursor() as cur:
        cur.execute(
            _ENTRY_SELECT + " JOIN organizations o ON o.id=j.org_id WHERE o.slug=%s" +
            condition + " ORDER BY j.occurred_at DESC, j.entry_id DESC LIMIT %s", params,
        )
        return [_public(row) for row in cur.fetchall()]
