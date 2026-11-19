"""Metadatos de adjuntos, alcance por organizacion y reintentos atomicos."""
from __future__ import annotations

import hashlib
from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel

from fierro_api.db import require_row
from fierro_api.media_storage import MediaStorage, ObjectConflict, StorageError
from fierro_api.media_validation import MediaError, validate_media


class AttachmentMissing(ValueError):
    """Entrada, relacion o adjunto fuera del alcance consultado."""


class AttachmentConflict(ValueError):
    """El identificador ya corresponde a otro envio."""


class AttachmentOut(BaseModel):
    attachment_id: UUID
    entry_id: UUID
    kind: str
    content_type: str
    byte_size: int
    duration_ms: int | None
    created_at: datetime


class AttachmentList(BaseModel):
    attachments: list[AttachmentOut]


class AttachmentLocation(BaseModel):
    url: str
    expires_at: datetime
    content_type: str


def _public(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "attachment_id": str(row["attachment_id"]), "entry_id": str(row["entry_id"]),
        "kind": row["kind"], "content_type": row["content_type"],
        "byte_size": row["byte_size"], "duration_ms": row["duration_ms"],
        "created_at": row["created_at"].isoformat(),
    }


def _entry(cur: Any, org: str, entry_id: UUID, tag: str | None) -> dict[str, Any]:
    cur.execute(
        "SELECT e.entry_id,e.org_id FROM journal_entries e JOIN organizations o "
        "ON o.id=e.org_id WHERE e.entry_id=%s AND o.slug=%s FOR UPDATE OF e", (entry_id, org),
    )
    entry = cur.fetchone()
    if entry is None:
        raise AttachmentMissing("Nota no encontrada")
    if tag is not None:
        cur.execute(
            "SELECT 1 FROM journal_entry_animals ea JOIN animals a ON a.id=ea.animal_id "
            "WHERE ea.entry_id=%s AND ea.org_id=%s AND a.tag_id=%s",
            (entry_id, entry["org_id"], tag),
        )
        if cur.fetchone() is None:
            raise AttachmentMissing("La nota no pertenece a ese animal")
    return dict(entry)


def upload(
    dsn: str, *, org: str, entry_id: UUID, attachment_id: UUID, kind: str,
    raw: bytes, content_type: str, storage: MediaStorage, tag: str | None = None,
) -> dict[str, Any]:
    import psycopg
    from psycopg.rows import dict_row

    digest = hashlib.sha256(raw).digest()
    declared = content_type.split(";")[0].strip().lower()
    with psycopg.connect(dsn, row_factory=dict_row) as conn, conn.cursor() as cur:
        entry = _entry(cur, org, entry_id, tag)
        # UUID global y fila de entrada bloqueados antes de consultar/escribir objetos.
        cur.execute("SELECT pg_advisory_xact_lock(%s)",
                    (int.from_bytes(attachment_id.bytes[:8], "big", signed=True),))
        cur.execute("SELECT * FROM journal_attachments WHERE attachment_id=%s", (attachment_id,))
        previous = cur.fetchone()
        if previous is not None:
            if (previous["entry_id"] != entry_id or previous["org_id"] != entry["org_id"]
                    or previous["sha256"] != digest or previous["kind"] != kind
                    or previous["content_type"] != declared):
                raise AttachmentConflict("Ese identificador ya corresponde a otro adjunto")
            return _public(previous)
        cur.execute(
            "SELECT count(*) FROM journal_attachments WHERE entry_id=%s AND kind=%s",
            (entry_id, kind),
        )
        if require_row(cur.fetchone(), "contar adjuntos")["count"] >= (6 if kind == "photo" else 2):
            raise MediaError("Cada nota admite hasta 6 fotos y 2 audios")
        clean, verified_type, duration = validate_media(raw, kind, content_type)
        key = f"org/{entry['org_id']}/journal/{entry_id}/{attachment_id}"
        try:
            generation = storage.put(key, clean, verified_type)
        except ObjectConflict as exc:
            raise AttachmentConflict(str(exc)) from exc
        except (OSError, StorageError) as exc:
            raise StorageError("No se pudo guardar el archivo. Reintenta el mismo envio") from exc
        cur.execute(
            "INSERT INTO journal_attachments(attachment_id,entry_id,org_id,kind,content_type,"
            "byte_size,duration_ms,sha256,storage_key,storage_generation) "
            "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING *",
            (attachment_id, entry_id, entry["org_id"], kind, verified_type, len(clean),
             duration, digest, key, generation),
        )
        return _public(dict(require_row(cur.fetchone(), "guardar adjunto")))


def list_for_entry(
    dsn: str, *, org: str, entry_id: UUID, tag: str | None = None,
) -> list[dict[str, Any]]:
    import psycopg
    from psycopg.rows import dict_row

    with psycopg.connect(dsn, row_factory=dict_row) as conn, conn.cursor() as cur:
        _entry(cur, org, entry_id, tag)
        cur.execute(
            "SELECT * FROM journal_attachments WHERE entry_id=%s "
            "ORDER BY created_at,attachment_id", (entry_id,),
        )
        return [_public(row) for row in cur.fetchall()]


def locate(
    dsn: str, *, org: str, entry_id: UUID, attachment_id: UUID, tag: str | None = None,
) -> dict[str, Any]:
    import psycopg
    from psycopg.rows import dict_row

    with psycopg.connect(dsn, row_factory=dict_row) as conn, conn.cursor() as cur:
        _entry(cur, org, entry_id, tag)
        cur.execute(
            "SELECT * FROM journal_attachments WHERE entry_id=%s AND attachment_id=%s",
            (entry_id, attachment_id),
        )
        row = cur.fetchone()
        if row is None:
            raise AttachmentMissing("Adjunto no encontrado")
        return dict(row)
