"""Copia de la lista de espera en una hoja de Google (#129).

La base es la fuente de verdad; la hoja es una copia para el equipo comercial.
Corre como job periodico (Cloud Run Job + Cloud Scheduler), nunca dentro de
`POST /v1/waitlist`: si Google falla, el registro no se entera.

Idempotencia: `waitlist_export.last_id` guarda el ultimo id copiado. Solo
avanza despues de que Google confirma el append, en la misma transaccion que
lo lee, con un lock que impide dos corridas a la vez. Si Google falla, el
cursor no se mueve y la siguiente corrida reintenta las mismas filas.

Credencial: ninguna llave en el repo ni en Secret Manager. En Cloud Run el
token sale del servidor de metadatos con la cuenta de servicio del job; la
hoja se comparte solo con ese correo.

    FIERRO_API_DSN=... FIERRO_WAITLIST_SHEET_ID=... python -m fierro_api.waitlist_sheet
"""

from __future__ import annotations

import json
import logging
import os
import sys
import urllib.parse
import urllib.request
from collections.abc import Callable
from typing import Any, Protocol

logger = logging.getLogger(__name__)

COLUMNAS = ["id", "fecha", "nombre", "correo", "estaciones", "consentimiento"]
_LOCK = 8113772
_SCOPE = "https://www.googleapis.com/auth/spreadsheets"
_METADATA_TOKEN = (
    "http://metadata.google.internal/computeMetadata/v1/instance/"
    "service-accounts/default/token?scopes=" + urllib.parse.quote(_SCOPE)
)


class SheetClient(Protocol):
    def append(self, rows: list[list[Any]]) -> None: ...


def _fila(r: dict[str, Any]) -> list[Any]:
    return [r["id"], r["created_at"].isoformat(), r["name"], r["email"], r["stations"],
            r["consent_version"]]


def sync(dsn: str, client: SheetClient, *, batch: int = 500) -> int:
    """Copia a la hoja las altas nuevas. Devuelve cuantas filas agrego."""
    import psycopg
    from psycopg.rows import dict_row

    with psycopg.connect(dsn, row_factory=dict_row) as conn, conn.cursor() as cur:
        cur.execute("SELECT pg_advisory_xact_lock(%s)", (_LOCK,))
        cur.execute("SELECT last_id FROM waitlist_export WHERE id = 1 FOR UPDATE")
        fila = cur.fetchone()
        last_id = fila["last_id"] if fila else 0
        cur.execute(
            "SELECT id, created_at, name, email, stations, consent_version FROM waitlist "
            "WHERE id > %s ORDER BY id LIMIT %s",
            (last_id, batch),
        )
        nuevas = cur.fetchall()
        if not nuevas:
            return 0
        try:
            client.append([_fila(r) for r in nuevas])
        except Exception:
            logger.exception("No se pudo copiar la lista de espera a la hoja; se reintenta "
                             "en la siguiente corrida (cursor en %s)", last_id)
            raise
        cur.execute(
            "UPDATE waitlist_export SET last_id = %s, updated_at = now() WHERE id = 1",
            (nuevas[-1]["id"],),
        )
        return len(nuevas)


def _token_de_metadatos() -> str:
    req = urllib.request.Request(_METADATA_TOKEN, headers={"Metadata-Flavor": "Google"})
    with urllib.request.urlopen(req, timeout=10) as resp:  # noqa: S310 - URL fija
        return str(json.load(resp)["access_token"])


class GoogleSheetsClient:
    """Append por la API REST de Sheets, sin dependencias nuevas."""

    def __init__(
        self,
        spreadsheet_id: str,
        rango: str = "Lista!A:F",
        token: Callable[[], str] = _token_de_metadatos,
    ) -> None:
        self.spreadsheet_id = spreadsheet_id
        self.rango = rango
        self.token = token

    def append(self, rows: list[list[Any]]) -> None:
        url = (
            "https://sheets.googleapis.com/v4/spreadsheets/"
            f"{urllib.parse.quote(self.spreadsheet_id)}/values/{urllib.parse.quote(self.rango)}"
            # RAW: un nombre que empieza con "=" se guarda como texto, no como formula.
            ":append?valueInputOption=RAW&insertDataOption=INSERT_ROWS"
        )
        req = urllib.request.Request(
            url,
            data=json.dumps({"values": rows}).encode(),
            method="POST",
            headers={"Authorization": f"Bearer {self.token()}",
                     "Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=30) as resp:  # noqa: S310 - host fijo
            resp.read()


def main() -> int:
    logging.basicConfig(level=logging.INFO)
    dsn = os.getenv("FIERRO_API_DSN", "").strip()
    sheet = os.getenv("FIERRO_WAITLIST_SHEET_ID", "").strip()
    if not dsn or not sheet:
        logger.error("Faltan FIERRO_API_DSN o FIERRO_WAITLIST_SHEET_ID")
        return 2
    try:
        n = sync(dsn, GoogleSheetsClient(sheet))
    except Exception:  # noqa: BLE001 - ya quedo en logs; el job marca fallo
        return 1
    logger.info("Lista de espera: %s filas nuevas en la hoja", n)
    return 0


if __name__ == "__main__":
    sys.exit(main())
