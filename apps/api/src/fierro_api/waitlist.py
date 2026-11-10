"""Lista de interés pública, independiente de las cuentas de acceso.

Dos límites (#74), los dos en PostgreSQL para que valgan entre réplicas:

- **Por cliente:** `CLIENT_LIMIT` intentos por hora, cuente o no como alta
  nueva (reintentar un correo existente también gasta). Es un solo upsert, así
  que el abuso se corta antes de tomar el lock y consultar la tabla.
- **Global:** `GLOBAL_LIMIT` altas nuevas por hora, de respaldo.

El cliente se guarda como HMAC de su IP con un secreto del servidor: sirve para
contar, no para saber quién es. Ver `client_ip` en `main.py` para de dónde sale
la IP y por qué no se confía en `X-Forwarded-For` a ciegas.
"""
import hashlib
import hmac
from typing import Any

CLIENT_LIMIT = 5
GLOBAL_LIMIT = 100


class WaitlistFull(Exception):
    pass


class TooManyFromClient(Exception):
    pass


def client_key(ip: str, secret: str) -> str:
    return hmac.new(secret.encode(), ip.encode(), hashlib.sha256).hexdigest()[:32]


def register(dsn: str, *, name: str, email: str, stations: int, client: str | None = None) -> None:
    import psycopg
    with psycopg.connect(dsn) as conn, conn.cursor() as cur:
        if client is not None:
            cur.execute(
                "INSERT INTO waitlist_rate(client, window_start, hits) "
                "VALUES (%s, date_trunc('hour', now()), 1) "
                "ON CONFLICT (client, window_start) DO UPDATE SET hits = waitlist_rate.hits + 1 "
                "RETURNING hits",
                (client,),
            )
            hits = cur.fetchone()
            if hits and hits[0] > CLIENT_LIMIT:
                conn.commit()  # el intento cuenta aunque se rechace
                raise TooManyFromClient
            cur.execute("DELETE FROM waitlist_rate WHERE window_start < now() - interval '1 day'")
        # Transaccional: el límite incluye las otras réplicas del servicio.
        cur.execute("SELECT pg_advisory_xact_lock(8113771)")
        cur.execute("SELECT 1 FROM waitlist WHERE email=%s", (email,))
        if cur.fetchone():
            return
        cur.execute("SELECT count(*) FROM waitlist WHERE created_at > now()-interval '1 hour'")
        count = cur.fetchone()
        if count and count[0] >= GLOBAL_LIMIT:
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
