"""Diario del rancho: entradas por organizacion con 0..n animales.

Autor del servidor y reintentos idempotentes por `entry_id`. Las rutas por
animal (`/v1/animals/{tag_id}/journal`) son una vista del mismo diario.
"""

from datetime import datetime
from typing import Any
from uuid import UUID, uuid5

from fierro_api.animals import _org_id

# Las entradas que salen del campo Notas de la ficha llevan un id derivado del
# cambio: un reintento del mismo guardado cae en el mismo id y no duplica.
_FICHA_NS = UUID("6f1c2b1e-5d0a-4a57-9a43-1f0f6e1b9c11")

_ENTRY_COLUMNS = (
    "e.entry_id, e.occurred_at, e.created_at, e.category, e.body, e.source, "
    "e.org_id, e.author_id, "
    "COALESCE(NULLIF(u.full_name,''), u.email, 'Notas de la ficha') AS author, "
    "COALESCE((SELECT array_agg(a.tag_id ORDER BY a.tag_id) "
    "  FROM journal_entry_animals ea JOIN animals a ON a.id=ea.animal_id "
    "  WHERE ea.entry_id=e.entry_id), '{}') AS animals "
)
_ENTRY_FROM = "FROM journal_entries e LEFT JOIN users u ON u.id=e.author_id "
_SELECT = "SELECT " + _ENTRY_COLUMNS + _ENTRY_FROM


class EntryConflict(ValueError):
    """La clave de reintento ya representa otra anotación."""


def _public(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "entry_id": str(row["entry_id"]),
        "occurred_at": row["occurred_at"].isoformat(),
        "created_at": row["created_at"].isoformat(),
        "category": row["category"], "body": row["body"],
        "author": row["author"], "animals": list(row["animals"]),
    }


def _animal_ids(cur: Any, org_id: int, tags: list[str]) -> list[int]:
    """Crea las fichas que falten (como ya hacía la bitácora) y da sus ids."""
    ids = []
    for tag in tags:
        cur.execute(
            "INSERT INTO animals(org_id, tag_id) VALUES (%s, %s) "
            "ON CONFLICT (org_id, tag_id) DO NOTHING", (org_id, tag),
        )
        cur.execute("SELECT id FROM animals WHERE org_id=%s AND tag_id=%s", (org_id, tag))
        animal = cur.fetchone()
        if animal is None:
            raise RuntimeError("No se pudo recuperar la ficha del animal")
        ids.append(animal["id"])
    return ids


def add_journal_entry(
    dsn: str, *, org: str, author_id: int, entry_id: UUID, occurred_at: datetime,
    category: str, body: str, tags: list[str],
) -> dict[str, Any]:
    """Entrada del diario con 0..n animales. Idempotente por `entry_id`."""
    import psycopg
    from psycopg.rows import dict_row

    tags = sorted(set(tags))
    with psycopg.connect(dsn, row_factory=dict_row) as conn, conn.cursor() as cur:
        org_id = _org_id(cur, org)
        animal_ids = _animal_ids(cur, org_id, tags)
        cur.execute(
            "INSERT INTO journal_entries"
            "(entry_id, org_id, author_id, occurred_at, category, body) "
            "VALUES (%s,%s,%s,%s,%s,%s) ON CONFLICT (entry_id) DO NOTHING RETURNING entry_id",
            (entry_id, org_id, author_id, occurred_at, category, body),
        )
        if cur.fetchone() is not None:
            for animal_id in animal_ids:
                cur.execute(
                    "INSERT INTO journal_entry_animals(entry_id, animal_id, org_id) "
                    "VALUES (%s,%s,%s)", (entry_id, animal_id, org_id),
                )
        cur.execute(_SELECT + "WHERE e.entry_id=%s", (entry_id,))
        row = cur.fetchone()
        if row is None:
            raise RuntimeError("No se pudo confirmar la anotación")
        # Mismo id con otro contenido, o de otra organización: no se pisa y no
        # se revela lo que hay guardado.
        if any(row[key] != value for key, value in {
            "org_id": org_id, "author_id": author_id, "occurred_at": occurred_at,
            "category": category, "body": body, "animals": tags,
        }.items()):
            raise EntryConflict("La clave ya corresponde a otra anotación.")
        return _public(row)


def add_entry(
    dsn: str, *, org: str, tag: str, author_id: int, entry_id: UUID,
    occurred_at: datetime, category: str, body: str,
) -> dict[str, Any]:
    """Anotación de un solo animal (ruta `/v1/animals/{tag_id}/journal`)."""
    return add_journal_entry(
        dsn, org=org, author_id=author_id, entry_id=entry_id,
        occurred_at=occurred_at, category=category, body=body, tags=[tag],
    )


def _journal_filters(
    org: str, tag: str | None, desde: datetime | None, hasta: datetime | None,
) -> tuple[str, list[Any]]:
    """Alcance y periodo compartidos por listado y busqueda."""
    condition = "WHERE e.org_id=(SELECT id FROM organizations WHERE slug=%s)"
    params: list[Any] = [org]
    if tag is not None:
        condition += (
            " AND EXISTS (SELECT 1 FROM journal_entry_animals ea "
            "JOIN animals a ON a.id=ea.animal_id "
            "WHERE ea.entry_id=e.entry_id AND a.tag_id=%s)"
        )
        params.append(tag)
    if desde is not None:
        condition += " AND e.occurred_at >= %s"
        params.append(desde)
    if hasta is not None:
        condition += " AND e.occurred_at < %s"
        params.append(hasta)
    return condition, params


def list_journal(
    dsn: str, *, org: str, limit: int, tag: str | None = None,
    desde: datetime | None = None, hasta: datetime | None = None,
    before: tuple[datetime, UUID] | None = None,
) -> list[dict[str, Any]]:
    """Entradas de UNA organización, más recientes primero.

    `desde` es inclusivo y `hasta` exclusivo. Con `tag`, solo las entradas que
    incluyen ese animal (también las que tienen varios).
    """
    import psycopg
    from psycopg.rows import dict_row

    condition, params = _journal_filters(org, tag, desde, hasta)
    if before:
        condition += " AND (e.occurred_at, e.entry_id) < (%s, %s)"
        params.extend(before)
    params.append(limit)
    with psycopg.connect(dsn, row_factory=dict_row) as conn, conn.cursor() as cur:
        cur.execute(
            _SELECT + condition + " ORDER BY e.occurred_at DESC, e.entry_id DESC LIMIT %s",
            params,
        )
        return [_public(row) for row in cur.fetchall()]


def search(
    dsn: str, *, org: str, query: str, tag: str | None = None,
    desde: datetime | None = None, hasta: datetime | None = None, limit: int = 10,
) -> list[dict[str, Any]]:
    """Coincidencias por relevancia, fecha y UUID, dentro de una organizacion.

    El fragmento es texto con marcas [[...]]. El consumidor lo muestra como
    texto. La obtencion de autores, animales y fragmentos se hace tras el LIMIT.
    """
    import psycopg
    from psycopg.rows import dict_row

    condition, params = _journal_filters(org, tag, desde, hasta)
    sql = (
        "WITH terms AS MATERIALIZED ("
        "SELECT websearch_to_tsquery('pg_catalog.spanish',public.fierro_unaccent(%s)) AS query"
        "), ranked AS MATERIALIZED ("
        "SELECT e.entry_id,ts_rank(e.search_tsv,terms.query) AS relevance "
        "FROM journal_entries e CROSS JOIN terms " + condition +
        " AND e.search_tsv @@ terms.query "
        "ORDER BY relevance DESC,e.occurred_at DESC,e.entry_id DESC LIMIT %s"
        ") SELECT " + _ENTRY_COLUMNS +
        ",ts_headline('pg_catalog.spanish',e.body,terms.query,"
        "'StartSel=[[, StopSel=]], MaxWords=35, MinWords=12, MaxFragments=1') AS excerpt "
        + _ENTRY_FROM +
        "JOIN ranked ON ranked.entry_id=e.entry_id CROSS JOIN terms "
        "ORDER BY ranked.relevance DESC,e.occurred_at DESC,e.entry_id DESC"
    )
    with psycopg.connect(dsn, row_factory=dict_row) as conn, conn.cursor() as cur:
        cur.execute(sql, [query.strip(), *params, limit])
        return [{**_public(row), "excerpt": row["excerpt"]} for row in cur.fetchall()]


def list_entries(
    dsn: str, *, org: str, tag: str, limit: int,
    before: tuple[datetime, UUID] | None = None,
) -> list[dict[str, Any]]:
    """Entradas de un animal: vista por ficha del diario."""
    return list_journal(dsn, org=org, tag=tag, limit=limit, before=before)


def record_ficha_note(
    cur: Any, *, org_id: int, animal_id: int, author_id: int | None,
    text: str, occurred_at: datetime,
) -> None:
    """El campo Notas ya no se sobrescribe: cada cambio queda como entrada `general`.

    Si el texto es igual a la nota vigente no se hace nada; así reenviar la ficha
    completa, que es lo que hace la web al guardar el alias, no duplica.
    """
    text = text.strip()
    if not text:
        return
    current = current_ficha_note(cur, animal_id)
    if current is not None and current["body"].strip() == text:
        return
    previous = str(current["entry_id"]) if current else "-"
    entry_id = uuid5(_FICHA_NS, f"{animal_id}:{previous}:{text}")
    cur.execute(
        "INSERT INTO journal_entries"
        "(entry_id, org_id, author_id, occurred_at, category, body, source) "
        "VALUES (%s,%s,%s,%s,'general',%s,'ficha') ON CONFLICT (entry_id) DO NOTHING "
        "RETURNING entry_id",
        (entry_id, org_id, author_id, occurred_at, text),
    )
    if cur.fetchone() is not None:
        cur.execute(
            "INSERT INTO journal_entry_animals(entry_id, animal_id, org_id) VALUES (%s,%s,%s)",
            (entry_id, animal_id, org_id),
        )


def current_ficha_note(cur: Any, animal_id: int) -> dict[str, Any] | None:
    """La nota vigente de la ficha: la última entrada que salió del campo Notas."""
    cur.execute(
        "SELECT e.entry_id, e.body FROM journal_entries e "
        "JOIN journal_entry_animals ea ON ea.entry_id=e.entry_id "
        "WHERE ea.animal_id=%s AND e.source='ficha' "
        "ORDER BY e.created_at DESC, e.entry_id DESC LIMIT 1",
        (animal_id,),
    )
    row = cur.fetchone()
    if row is None:
        return None
    return dict(row) if isinstance(row, dict) else {"entry_id": row[0], "body": row[1]}
