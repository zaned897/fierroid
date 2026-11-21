"""Ledger de dinero por organización. Solo inserciones y consultas."""
from datetime import UTC, date, datetime
from typing import Any
from uuid import UUID

from fierro_api.animals import _org_id
from fierro_api.db import require_row
from fierro_api.dinero_models import MovementIn, VoidIn

_FIELDS = (
    "movement_id", "kind", "category", "amount_mxn", "precio_kg_mxn", "weight_kg",
    "occurred_on", "period_start", "period_end", "scope", "corral", "source_entry_id",
)
_SELECT = (
    "SELECT m.*, COALESCE(NULLIF(u.full_name,''),u.email) AS author, "
    "COALESCE((SELECT array_agg(a.tag_id ORDER BY a.tag_id) "
    "FROM money_movement_animals ma JOIN animals a ON a.id=ma.animal_id "
    "WHERE ma.movement_id=m.movement_id AND ma.org_id=m.org_id),'{}') AS animals "
    "FROM money_movements_ledger m JOIN users u ON u.id=m.author_id "
)


class MovementConflict(ValueError):
    """La clave o el movimiento ya representan otra operación."""


class MovementMissing(ValueError):
    """El movimiento no existe en la organización seleccionada."""


def _public(row: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in row.items() if key != "org_id"}


def _lock_key(cur: Any, key: UUID) -> None:
    cur.execute("SELECT pg_advisory_xact_lock(%s)", (
        int.from_bytes(key.bytes[:8], "big", signed=True),
    ))


def _find(cur: Any, movement_id: UUID) -> dict[str, Any] | None:
    cur.execute(_SELECT + "WHERE m.movement_id=%s", (movement_id,))
    row = cur.fetchone()
    return dict(row) if row is not None else None


def _animals(cur: Any, org_id: int, tags: list[str]) -> list[int]:
    cur.execute("SELECT id,tag_id FROM animals WHERE org_id=%s AND tag_id=ANY(%s) "
                "ORDER BY tag_id", (org_id, tags))
    rows = cur.fetchall()
    missing = set(tags) - {row["tag_id"] for row in rows}
    if missing:
        raise ValueError("Algún animal no está registrado en esta organización: "
                         + ", ".join(sorted(missing)))
    return [row["id"] for row in rows]


def _insert(cur: Any, data: dict[str, Any], org_id: int, author_id: int,
            animal_ids: list[int], voids: UUID | None = None) -> dict[str, Any]:
    columns = ",".join(_FIELDS) + ",org_id,author_id,voids_movement_id"
    slots = ",".join(["%s"] * (len(_FIELDS) + 3))
    cur.execute(f"INSERT INTO money_movements({columns}) VALUES ({slots})",
                (*[data[key] for key in _FIELDS], org_id, author_id, voids))
    for animal_id in animal_ids:
        cur.execute("INSERT INTO money_movement_animals(movement_id,animal_id,org_id) "
                    "VALUES (%s,%s,%s)", (data["movement_id"], animal_id, org_id))
    return _public(require_row(_find(cur, data["movement_id"]), "movimiento creado"))


def add(dsn: str, *, org: str, author_id: int, movement: MovementIn) -> dict[str, Any]:
    import psycopg
    from psycopg.rows import dict_row

    data = movement.model_dump()
    with psycopg.connect(dsn, row_factory=dict_row) as conn, conn.cursor() as cur:
        org_id = _org_id(cur, org)
        _lock_key(cur, movement.movement_id)
        existing = _find(cur, movement.movement_id)
        if existing is not None:
            if existing["org_id"] != org_id or existing["author_id"] != author_id \
                    or existing["voids_movement_id"] is not None \
                    or any(existing[key] != data[key] for key in _FIELDS) \
                    or set(existing["animals"]) != set(movement.animals):
                raise MovementConflict("La clave ya corresponde a otro movimiento")
            return _public(existing)
        animal_ids = _animals(cur, org_id, movement.animals)
        if movement.kind in ("compra", "venta"):
            # Serializa la comprobación y la inserción para el mismo animal,
            # incluso cuando aún no tiene movimientos que se puedan bloquear.
            cur.execute("SELECT id FROM animals WHERE org_id=%s AND id=%s FOR UPDATE",
                        (org_id, animal_ids[0]))
            # Mismas reglas que dinero.py (#199): una compra y una venta vigentes
            # como máximo, y la venta no antes de la compra.
            cur.execute("SELECT m.kind, m.occurred_on FROM money_movements_ledger m "
                        "JOIN money_movement_animals ma ON ma.movement_id=m.movement_id "
                        "AND ma.org_id=m.org_id WHERE m.org_id=%s AND ma.animal_id=%s "
                        "AND m.kind IN ('compra','venta') AND m.estado='confirmado'",
                        (org_id, animal_ids[0]))
            for previo in cur.fetchall():
                if previo["kind"] == movement.kind:
                    raise MovementConflict(f"El animal ya tiene una {movement.kind} vigente")
                if movement.kind == "venta" and movement.occurred_on < previo["occurred_on"]:
                    raise MovementConflict("La venta no puede tener fecha anterior a la compra")
                if movement.kind == "compra" and movement.occurred_on > previo["occurred_on"]:
                    raise MovementConflict("La compra no puede tener fecha posterior a la venta")
        if movement.source_entry_id is not None:
            cur.execute("SELECT 1 FROM journal_entries WHERE entry_id=%s AND org_id=%s",
                        (movement.source_entry_id, org_id))
            if cur.fetchone() is None:
                raise ValueError("La nota de origen no existe en esta organización")
        return _insert(cur, data, org_id, author_id, animal_ids)


def void(dsn: str, *, org: str, author_id: int, original_id: UUID,
         operation: VoidIn) -> dict[str, Any]:
    import psycopg
    from psycopg.rows import dict_row

    with psycopg.connect(dsn, row_factory=dict_row) as conn, conn.cursor() as cur:
        org_id = _org_id(cur, org)
        _lock_key(cur, operation.movement_id)
        # Serializa anulaciones simultáneas del mismo original.
        cur.execute("SELECT movement_id FROM money_movements WHERE movement_id=%s "
                    "AND org_id=%s FOR UPDATE", (original_id, org_id))
        if cur.fetchone() is None:
            raise MovementMissing("No se encontró el movimiento")
        original = require_row(_find(cur, original_id), "movimiento original")
        existing = _find(cur, operation.movement_id)
        if existing is not None:
            if (existing["org_id"], existing["author_id"], existing["voids_movement_id"],
                existing["occurred_on"]) != (org_id, author_id, original_id,
                                            operation.occurred_on):
                raise MovementConflict("La clave ya corresponde a otro movimiento")
            return _public(existing)
        if original["estado"] != "confirmado" or original["voids_movement_id"] is not None:
            raise MovementConflict("El movimiento ya fue anulado o es una anulación")
        data = {key: original[key] for key in _FIELDS}
        data.update(movement_id=operation.movement_id, occurred_on=operation.occurred_on)
        ids = _animals(cur, org_id, original["animals"])
        return _insert(cur, data, org_id, author_id, ids, original_id)


def list_movements(dsn: str, *, org: str, animal: str | None = None,
                   desde: date | None = None, hasta: date | None = None,
                   kind: str | None = None, estado: str = "vigente") -> list[dict[str, Any]]:
    """Fechas de evento inclusivas; todos incluye originales y anulaciones."""
    import psycopg
    from psycopg.rows import dict_row

    where = "WHERE m.org_id=(SELECT id FROM organizations WHERE slug=%s)"
    params: list[Any] = [org]
    for name, value, operator in (("occurred_on", desde, ">="), ("occurred_on", hasta, "<="),
                                  ("kind", kind, "=")):
        if value is not None:
            where += f" AND m.{name}{operator}%s"
            params.append(value)
    if estado != "todos":
        where += " AND m.estado=%s"
        params.append("confirmado" if estado == "vigente" else estado)
    if animal is not None:
        where += (" AND EXISTS (SELECT 1 FROM money_movement_animals ma JOIN animals a "
                  "ON a.id=ma.animal_id WHERE ma.movement_id=m.movement_id "
                  "AND ma.org_id=m.org_id AND a.tag_id=%s)")
        params.append(animal)
    with psycopg.connect(dsn, row_factory=dict_row) as conn, conn.cursor() as cur:
        cur.execute(_SELECT + where + " ORDER BY m.occurred_on DESC,m.created_at DESC,"
                    "m.movement_id DESC", params)
        return [_public(dict(row)) for row in cur.fetchall()]


def price(dsn: str, *, org: str) -> dict[str, Any]:
    history = list_movements(dsn, org=org, kind="precio_mercado", estado="todos")
    today = datetime.now(UTC).date()
    current = next((row for row in history if row["estado"] == "confirmado"
                    and row["occurred_on"] <= today), None)
    return {"current": current, "history": history}
