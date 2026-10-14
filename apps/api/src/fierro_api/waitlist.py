"""Lista de interes publica, independiente de las cuentas de acceso."""

from __future__ import annotations

import hashlib
import io
import secrets
import smtplib
import zipfile
from dataclasses import dataclass
from email.message import EmailMessage
from typing import Any
from xml.sax.saxutils import escape


class WaitlistFull(Exception):
    pass


class MailDeliveryError(Exception):
    pass


@dataclass(frozen=True)
class RegistrationResult:
    email: str
    name: str
    token: str | None
    confirmed: bool
    created: bool


@dataclass(frozen=True)
class MailConfig:
    host: str
    port: int
    from_email: str
    username: str = ""
    password: str = ""
    starttls: bool = True

    @property
    def ready(self) -> bool:
        return bool(self.host and self.port and self.from_email)


def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _serialize(row: dict[str, Any]) -> dict[str, Any]:
    return {
        **row,
        "created_at": row["created_at"].isoformat(),
        "confirmation_sent_at": row["confirmation_sent_at"].isoformat()
        if row.get("confirmation_sent_at")
        else None,
        "confirmed_at": row["confirmed_at"].isoformat()
        if row.get("confirmed_at")
        else None,
    }


def register(
    dsn: str, *, name: str, email: str, state: str, stations: int
) -> RegistrationResult:
    import psycopg
    from psycopg.rows import dict_row

    token = secrets.token_urlsafe(32)
    token_hash = _token_hash(token)
    with psycopg.connect(dsn, row_factory=dict_row) as conn, conn.cursor() as cur:
        # Transaccional: el limite incluye las otras replicas del servicio.
        cur.execute("SELECT pg_advisory_xact_lock(8113771)")
        cur.execute(
            """
            SELECT id,name,email,confirmed_at
            FROM waitlist
            WHERE email=%s
            """,
            (email,),
        )
        existing = cur.fetchone()
        if existing:
            if existing["confirmed_at"]:
                return RegistrationResult(
                    email=existing["email"],
                    name=existing["name"],
                    token=None,
                    confirmed=True,
                    created=False,
                )
            cur.execute(
                """
                UPDATE waitlist
                SET confirmation_token_hash=%s,
                    confirmation_sent_at=now(),
                    state=%s
                WHERE id=%s
                """,
                (token_hash, state, existing["id"]),
            )
            return RegistrationResult(
                email=existing["email"],
                name=existing["name"],
                token=token,
                confirmed=False,
                created=False,
            )

        cur.execute(
            "SELECT count(*) FROM waitlist WHERE created_at > now()-interval '1 hour'"
        )
        count = cur.fetchone()
        if count and count["count"] >= 100:
            raise WaitlistFull
        cur.execute(
            """
            INSERT INTO waitlist(
              name,email,state,stations,confirmation_token_hash,confirmation_sent_at
            )
            VALUES (%s,%s,%s,%s,%s,now())
            """,
            (name, email, state, stations, token_hash),
        )
    return RegistrationResult(
        email=email,
        name=name,
        token=token,
        confirmed=False,
        created=True,
    )


def confirm(dsn: str, token: str) -> dict[str, Any] | None:
    if len(token) > 200:
        return None

    import psycopg
    from psycopg.rows import dict_row

    with psycopg.connect(dsn, row_factory=dict_row) as conn, conn.cursor() as cur:
        cur.execute(
            """
            UPDATE waitlist
            SET confirmed_at=COALESCE(confirmed_at, now())
            WHERE confirmation_token_hash=%s
            RETURNING id,name,email,state,stations,created_at,confirmation_sent_at,confirmed_at
            """,
            (_token_hash(token),),
        )
        row = cur.fetchone()
    return _serialize(row) if row else None


def list_entries(dsn: str, before: int | None, limit: int) -> list[dict[str, Any]]:
    import psycopg
    from psycopg.rows import dict_row

    with psycopg.connect(dsn, row_factory=dict_row) as conn, conn.cursor() as cur:
        cur.execute(
            """
            SELECT id,name,email,state,stations,created_at,confirmation_sent_at,confirmed_at
            FROM waitlist
            WHERE (%s::bigint IS NULL OR id < %s)
            ORDER BY id DESC
            LIMIT %s
            """,
            (before, before, limit),
        )
        return [_serialize(r) for r in cur.fetchall()]


def list_all_entries(dsn: str) -> list[dict[str, Any]]:
    import psycopg
    from psycopg.rows import dict_row

    with psycopg.connect(dsn, row_factory=dict_row) as conn, conn.cursor() as cur:
        cur.execute(
            """
            SELECT id,name,email,state,stations,created_at,confirmation_sent_at,confirmed_at
            FROM waitlist
            ORDER BY id DESC
            """
        )
        return [_serialize(r) for r in cur.fetchall()]


def send_confirmation_email(
    config: MailConfig, *, to_email: str, name: str, confirmation_url: str
) -> bool:
    if not config.ready:
        return False

    msg = EmailMessage()
    msg["Subject"] = "Confirma tu registro en Fierro"
    msg["From"] = config.from_email
    msg["To"] = to_email
    msg.set_content(
        f"Hola {name},\n\n"
        "Gracias por unirte a la lista de espera de Fierro.\n"
        "Confirma tu correo aqui:\n\n"
        f"{confirmation_url}\n\n"
        "Si no solicitaste este registro, puedes ignorar este mensaje.\n"
    )

    try:
        with smtplib.SMTP(config.host, config.port, timeout=15) as smtp:
            if config.starttls:
                smtp.starttls()
            if config.username:
                smtp.login(config.username, config.password)
            smtp.send_message(msg)
    except (OSError, smtplib.SMTPException) as exc:
        raise MailDeliveryError(str(exc)) from exc
    return True


def build_xlsx(entries: list[dict[str, Any]]) -> bytes:
    headers = [
        "ID",
        "Nombre",
        "Correo",
        "Estado",
        "Estaciones",
        "Estatus",
        "Registro",
        "Fecha confirmacion",
    ]
    rows = [headers]
    for entry in entries:
        rows.append(
            [
                entry["id"],
                entry["name"],
                entry["email"],
                entry["state"],
                entry["stations"],
                "Confirmado" if entry.get("confirmed_at") else "Pendiente",
                entry["created_at"],
                entry.get("confirmed_at") or "",
            ]
        )

    sheet_xml = _worksheet_xml(rows)
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as workbook:
        workbook.writestr(
            "[Content_Types].xml",
            """<?xml version="1.0" encoding="UTF-8"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>
  <Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>
  <Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>
</Types>""",
        )
        workbook.writestr(
            "_rels/.rels",
            """<?xml version="1.0" encoding="UTF-8"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>
</Relationships>""",
        )
        workbook.writestr(
            "xl/workbook.xml",
            """<?xml version="1.0" encoding="UTF-8"?>
<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
  <sheets>
    <sheet name="Lista de espera" sheetId="1" r:id="rId1"/>
  </sheets>
</workbook>""",
        )
        workbook.writestr(
            "xl/_rels/workbook.xml.rels",
            """<?xml version="1.0" encoding="UTF-8"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>
  <Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>
</Relationships>""",
        )
        workbook.writestr(
            "xl/styles.xml",
            """<?xml version="1.0" encoding="UTF-8"?>
<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
  <fonts count="1"><font><sz val="11"/><name val="Calibri"/></font></fonts>
  <fills count="1"><fill><patternFill patternType="none"/></fill></fills>
  <borders count="1"><border/></borders>
  <cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs>
  <cellXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/></cellXfs>
</styleSheet>""",
        )
        workbook.writestr("xl/worksheets/sheet1.xml", sheet_xml)
    return buffer.getvalue()


def _worksheet_xml(rows: list[list[Any]]) -> str:
    sheet_rows = []
    for row_index, row in enumerate(rows, start=1):
        cells = "".join(
            _inline_cell(row_index, col_index, value)
            for col_index, value in enumerate(row, start=1)
        )
        sheet_rows.append(f'<row r="{row_index}">{cells}</row>')
    last_row = max(len(rows), 1)
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
  <dimension ref="A1:H{last_row}"/>
  <cols>
    <col min="1" max="1" width="10" customWidth="1"/>
    <col min="2" max="3" width="28" customWidth="1"/>
    <col min="4" max="4" width="18" customWidth="1"/>
    <col min="5" max="5" width="12" customWidth="1"/>
    <col min="6" max="8" width="22" customWidth="1"/>
  </cols>
  <sheetData>
    {''.join(sheet_rows)}
  </sheetData>
</worksheet>"""


def _inline_cell(row: int, col: int, value: Any) -> str:
    address = f"{_column_name(col)}{row}"
    text = escape("" if value is None else str(value))
    return f'<c r="{address}" t="inlineStr"><is><t>{text}</t></is></c>'


def _column_name(index: int) -> str:
    name = ""
    while index:
        index, remainder = divmod(index - 1, 26)
        name = chr(65 + remainder) + name
    return name
