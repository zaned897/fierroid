"""Fichas de animales y sus fotos.

Las fotos viven en Postgres (`animal_photos`) a proposito: a escala piloto son
decenas de MB, entran en el respaldo de la base y no obligan a decidir el
proveedor de nube, que sigue abierto.

Todo lo que toca el binario esta en este modulo y en esa tabla. Cuando las
fotos se muevan a almacenamiento de objetos, se reemplazan `load_photo` y
`save_photo` y nada mas; el resto del sistema no sabe donde viven.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from psycopg import Cursor

from fierro_api.db import require_row

logger = logging.getLogger(__name__)

# 2 MB. La PWA reduce la imagen antes de subirla, asi que esto es el tope de
# seguridad, no el tamano esperado.
MAX_PHOTO_BYTES = 2 * 1024 * 1024

# SVG queda fuera a proposito: puede llevar script dentro, y lo servimos desde
# nuestro propio origen.
FIRMAS = {
    "image/jpeg": (b"\xff\xd8\xff",),
    "image/png": (b"\x89PNG\r\n\x1a\n",),
    "image/webp": (b"RIFF",),
}


class PhotoError(ValueError):
    """La imagen no es utilizable."""


@dataclass(frozen=True)
class Photo:
    bytes_: bytes
    content_type: str
    updated_at: datetime


def validate_photo(raw: bytes, declared_type: str | None) -> str:
    """Devuelve el content type verificado. Lanza PhotoError si no sirve.

    El tipo declarado por el cliente no se cree: se comprueba contra los bytes
    magicos. Si no, subir un HTML diciendo que es un JPEG lo convierte en XSS
    servido desde nuestro dominio.
    """
    if not raw:
        raise PhotoError("El archivo esta vacio")
    if len(raw) > MAX_PHOTO_BYTES:
        raise PhotoError(
            f"La imagen pesa {len(raw) // 1024} KB y el maximo es "
            f"{MAX_PHOTO_BYTES // 1024} KB"
        )

    normalizado = (declared_type or "").split(";")[0].strip().lower()
    if normalizado not in FIRMAS:
        raise PhotoError("Solo se aceptan imagenes JPEG, PNG o WebP")

    if not any(raw.startswith(firma) for firma in FIRMAS[normalizado]):
        raise PhotoError("El contenido del archivo no coincide con su tipo declarado")

    return normalizado


def _org_id(cur: "Cursor[Any]", org_slug: str) -> int:
    cur.execute("SELECT id FROM organizations WHERE slug = %s", (org_slug,))
    fila = cur.fetchone()
    if fila is None:
        raise ValueError(f"la organizacion {org_slug!r} no existe")
    # El cursor puede venir con dict_row o sin el, segun quien llame.
    return int(fila["id"] if isinstance(fila, dict) else fila[0])


def upsert_animal(
    dsn: str,
    *,
    org_slug: str,
    tag_id: str,
    alias: str | None = None,
    notes: str | None = None,
) -> dict[str, Any]:
    """Crea o actualiza la ficha. Idempotente por (organizacion, arete)."""
    import psycopg
    from psycopg.rows import dict_row

    with psycopg.connect(dsn, row_factory=dict_row) as conn, conn.cursor() as cur:
        org_id = _org_id(cur, org_slug)
        cur.execute(
            """
            INSERT INTO animals (org_id, tag_id, alias, notes)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (org_id, tag_id) DO UPDATE SET
              alias      = COALESCE(EXCLUDED.alias, animals.alias),
              notes      = COALESCE(EXCLUDED.notes, animals.notes),
              updated_at = now()
            RETURNING id, tag_id, alias, notes, created_at, updated_at
            """,
            (org_id, tag_id, alias, notes),
        )
        fila = dict(require_row(cur.fetchone(), "guardar ficha del animal"))
        conn.commit()

    fila["created_at"] = fila["created_at"].isoformat()
    fila["updated_at"] = fila["updated_at"].isoformat()
    return fila


def list_animals(dsn: str, *, org_slug: str | None = None) -> list[dict[str, Any]]:
    """El hato de la organizacion, con su ultimo peso y si tiene foto.

    La lista sale de lo que se ha PESADO, no de fichas creadas a mano: el hato
    lo definen los animales que pasaron por la manga. La fila en `animals` es
    metadato opcional que aparece cuando alguien pone nombre o sube foto.

    Nunca selecciona el binario de la foto: eso es lo que la mantiene barata.
    """
    import psycopg
    from psycopg.rows import dict_row

    with psycopg.connect(dsn, row_factory=dict_row) as conn, conn.cursor() as cur:
        cur.execute(
            """
            WITH alcance AS (
              SELECT id, slug FROM organizations
              WHERE %(org)s::text IS NULL OR slug = %(org)s
            ),
            tags AS (
              -- Animales pesados en alguna estacion de la organizacion.
              SELECT DISTINCT o.id AS org_id, o.slug AS org, r.tag_id
              FROM readings r
              JOIN devices d ON d.device_id = r.device_id
              JOIN ranches ra ON ra.id = d.ranch_id
              JOIN alcance o ON o.id = ra.org_id
              UNION
              -- Mas los que tienen ficha aunque todavia no se hayan pesado.
              SELECT o.id, o.slug, a.tag_id
              FROM animals a JOIN alcance o ON o.id = a.org_id
            )
            SELECT t.tag_id, t.org, a.alias, a.notes,
                   (ph.animal_id IS NOT NULL) AS has_photo,
                   u.weight_kg AS last_weight_kg,
                   u.captured_at AS last_captured_at,
                   COALESCE(u.total, 0) AS readings
            FROM tags t
            LEFT JOIN animals a ON a.org_id = t.org_id AND a.tag_id = t.tag_id
            LEFT JOIN animal_photos ph ON ph.animal_id = a.id
            LEFT JOIN LATERAL (
              SELECT r.weight_kg, r.captured_at, count(*) OVER () AS total
              FROM readings r
              JOIN devices d ON d.device_id = r.device_id
              JOIN ranches ra ON ra.id = d.ranch_id
              WHERE r.tag_id = t.tag_id AND ra.org_id = t.org_id
              ORDER BY r.captured_at DESC
              LIMIT 1
            ) u ON true
            ORDER BY a.alias NULLS LAST, t.tag_id
            """,
            {"org": org_slug},
        )
        filas = [dict(f) for f in cur.fetchall()]

    for fila in filas:
        if fila["last_captured_at"]:
            fila["last_captured_at"] = fila["last_captured_at"].isoformat()
    return filas


def get_animal(dsn: str, *, tag_id: str, org_slug: str | None = None) -> dict[str, Any] | None:
    animales = [a for a in list_animals(dsn, org_slug=org_slug) if a["tag_id"] == tag_id]
    return animales[0] if animales else None


def save_photo(
    dsn: str, *, org_slug: str, tag_id: str, raw: bytes, content_type: str
) -> dict[str, Any]:
    """Guarda la foto. Crea la ficha si no existia."""
    import psycopg

    with psycopg.connect(dsn) as conn, conn.cursor() as cur:
        org_id = _org_id(cur, org_slug)
        cur.execute(
            """
            INSERT INTO animals (org_id, tag_id) VALUES (%s, %s)
            ON CONFLICT (org_id, tag_id) DO UPDATE SET updated_at = now()
            RETURNING id
            """,
            (org_id, tag_id),
        )
        animal_id = require_row(cur.fetchone(), "crear ficha para la foto")[0]
        cur.execute(
            """
            INSERT INTO animal_photos (animal_id, bytes, content_type, byte_size)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (animal_id) DO UPDATE SET
              bytes        = EXCLUDED.bytes,
              content_type = EXCLUDED.content_type,
              byte_size    = EXCLUDED.byte_size,
              updated_at   = now()
            """,
            (animal_id, raw, content_type, len(raw)),
        )
        conn.commit()

    return {"tag_id": tag_id, "content_type": content_type, "byte_size": len(raw)}


def load_photo(dsn: str, *, tag_id: str, org_slug: str | None = None) -> Photo | None:
    import psycopg
    from psycopg.rows import dict_row

    condicion = "WHERE a.tag_id = %s"
    parametros: list[Any] = [tag_id]
    if org_slug is not None:
        condicion += " AND o.slug = %s"
        parametros.append(org_slug)

    with psycopg.connect(dsn, row_factory=dict_row) as conn, conn.cursor() as cur:
        cur.execute(
            f"""
            SELECT p.bytes, p.content_type, p.updated_at
            FROM animal_photos p
            JOIN animals a ON a.id = p.animal_id
            JOIN organizations o ON o.id = a.org_id
            {condicion}
            """,
            parametros,
        )
        fila = cur.fetchone()

    if fila is None:
        return None
    return Photo(
        bytes_=bytes(fila["bytes"]),
        content_type=fila["content_type"],
        updated_at=fila["updated_at"],
    )


def delete_photo(dsn: str, *, tag_id: str, org_slug: str | None = None) -> bool:
    import psycopg

    condicion = "a.tag_id = %s"
    parametros: list[Any] = [tag_id]
    if org_slug is not None:
        condicion += " AND o.slug = %s"
        parametros.append(org_slug)

    with psycopg.connect(dsn) as conn, conn.cursor() as cur:
        cur.execute(
            f"""
            DELETE FROM animal_photos p
            USING animals a, organizations o
            WHERE p.animal_id = a.id AND o.id = a.org_id AND {condicion}
            """,
            parametros,
        )
        borradas = cur.rowcount
        conn.commit()
    return borradas > 0
