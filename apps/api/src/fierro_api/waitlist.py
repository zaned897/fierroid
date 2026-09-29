"""Lista de interés pública, independiente de las cuentas de acceso."""
from typing import Any


class WaitlistFull(Exception):
    pass


def register(dsn: str, *, name: str, email: str, stations: int) -> None:
    import psycopg
    with psycopg.connect(dsn) as conn, conn.cursor() as cur:
        # Transaccional: el límite incluye las otras réplicas del servicio.
        cur.execute("SELECT pg_advisory_xact_lock(8113771)")
        cur.execute("SELECT 1 FROM waitlist WHERE email=%s", (email,))
        if cur.fetchone():
            return
        cur.execute("SELECT count(*) FROM waitlist WHERE created_at > now()-interval '1 hour'")
        count = cur.fetchone()
        if count and count[0] >= 100:
            raise WaitlistFull
        cur.execute("INSERT INTO waitlist(name,email,stations) VALUES (%s,%s,%s)",
                    (name, email, stations))


def list_entries(dsn: str, before: int | None, limit: int) -> list[dict[str, Any]]:
    import psycopg
    from psycopg.rows import dict_row
    with psycopg.connect(dsn, row_factory=dict_row) as conn, conn.cursor() as cur:
        cur.execute("SELECT id,name,email,stations,created_at FROM waitlist "
                    "WHERE (%s::bigint IS NULL OR id < %s) ORDER BY id DESC LIMIT %s",
                    (before, before, limit))
        return [{**r, "created_at": r["created_at"].isoformat()} for r in cur.fetchall()]
