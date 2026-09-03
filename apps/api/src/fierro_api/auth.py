"""Usuarios, credenciales y API keys.

La credencial de sesion es una **API key revocable**, no un JWT. Un JWT no se
puede invalidar antes de que expire; una API key vive como hash en la base, asi
que cerrar sesion es borrar una fila. Eso tambien hace posible "cerrar sesion en
todos los dispositivos" y cortar el acceso de alguien que se va del equipo.

El camino normal para entrar es Google (ver google_auth.py): nadie del equipo
gestiona contrasenas de terceros. La contrasena queda como via de respaldo para
cuentas administrativas y para las pruebas, y es opcional en el esquema.

Solo Postgres: el modo SQLite es de laboratorio y de un solo inquilino.
"""

from __future__ import annotations

import argparse
import getpass
import hashlib
import logging
import secrets
import sys
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError

from fierro_api.db import require_row

# argon2id con parametros por defecto de argon2-cffi, que siguen la
# recomendacion de OWASP. Subirlos es una decision de operacion, no de codigo.
_hasher = PasswordHasher()

# Hash desechable para gastar el mismo tiempo cuando el correo no existe.
# Sin esto, la diferencia de latencia revela que cuentas estan registradas.
_DUMMY_HASH = _hasher.hash("no-such-user-timing-guard")

logger = logging.getLogger(__name__)

# Prefijo reconocible: si una llave se filtra en un log o en un repositorio,
# es identificable de un vistazo y por los escaneres de secretos.
KEY_PREFIX = "fierro_"
KEY_PREFIX_VISIBLE = 14


class AuthError(Exception):
    """Credenciales invalidas o credencial no utilizable."""


@dataclass(frozen=True)
class AuthUser:
    id: int
    email: str
    org_id: int | None
    org_slug: str | None
    is_superuser: bool
    full_name: str | None = None

    def to_public(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "email": self.email,
            "full_name": self.full_name,
            "org": self.org_slug,
            "is_superuser": self.is_superuser,
        }


# ---------------------------------------------------------------------------
# Contrasenas (via de respaldo; el camino normal es Google)
# ---------------------------------------------------------------------------


def hash_password(plain: str) -> str:
    if len(plain) < 8:
        raise ValueError("la contrasena debe tener al menos 8 caracteres")
    return _hasher.hash(plain)


def verify_password(stored_hash: str, plain: str) -> bool:
    try:
        return _hasher.verify(stored_hash, plain)
    except (VerifyMismatchError, VerificationError):
        return False
    except InvalidHashError:
        # El hash guardado esta malformado. InvalidHashError hereda de
        # ValueError, no de VerificationError, asi que no lo cubre el except de
        # arriba: sin esta rama, una fila danada devuelve 500 en vez de 401.
        #
        # Se devuelve False porque la autenticacion falla de verdad, pero se
        # registra: una fila corrupta es un problema de datos que alguien tiene
        # que ver, no algo que tragarse en silencio.
        logger.error("hash de contrasena malformado en la base de datos")
        return False


# ---------------------------------------------------------------------------
# API keys
# ---------------------------------------------------------------------------


def _hash_key(plain: str) -> str:
    """SHA-256, no argon2.

    La llave son 256 bits aleatorios: no hay diccionario que la adivine, asi
    que un hash lento no protege de nada. Y se verifica en CADA request, donde
    argon2 costaria ~80 ms. argon2 es para secretos que elige un humano.
    """
    return hashlib.sha256(plain.encode()).hexdigest()


def generate_api_key() -> tuple[str, str, str]:
    """Devuelve (llave_en_claro, hash, prefijo_visible)."""
    plain = KEY_PREFIX + secrets.token_urlsafe(32)
    return plain, _hash_key(plain), plain[:KEY_PREFIX_VISIBLE]


def issue_api_key(
    dsn: str, *, user_id: int, name: str | None = None, ttl_days: int | None = 90
) -> dict[str, Any]:
    """Emite una llave nueva. La version en claro se devuelve UNA sola vez."""
    import psycopg

    plain, key_hash, prefix = generate_api_key()
    expires_at = (
        datetime.now(timezone.utc) + timedelta(days=ttl_days) if ttl_days else None
    )

    with psycopg.connect(dsn) as conn, conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO api_keys (user_id, key_hash, key_prefix, name, expires_at)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING id, created_at
            """,
            (user_id, key_hash, prefix, name, expires_at),
        )
        key_id, created_at = require_row(cur.fetchone(), "emitir API key")
        conn.commit()

    return {
        "api_key": plain,
        "id": key_id,
        "key_prefix": prefix,
        "created_at": created_at.isoformat(),
        "expires_at": expires_at.isoformat() if expires_at else None,
    }


def user_for_api_key(dsn: str, plain: str) -> AuthUser | None:
    """Resuelve el usuario de una llave, o None si no sirve."""
    import psycopg
    from psycopg.rows import dict_row

    with psycopg.connect(dsn, row_factory=dict_row) as conn, conn.cursor() as cur:
        cur.execute(
            _SELECT_USER
            + """
            JOIN api_keys k ON k.user_id = u.id
            WHERE k.key_hash = %s
              AND k.revoked_at IS NULL
              AND (k.expires_at IS NULL OR k.expires_at > now())
              AND u.is_active
            """,
            (_hash_key(plain),),
        )
        row = cur.fetchone()
        if row is None:
            return None

        # Solo se escribe si pasaron 5 minutos: sin esto seria un UPDATE por
        # cada request, y el dato no necesita ese detalle.
        cur.execute(
            """
            UPDATE api_keys SET last_used_at = now()
            WHERE key_hash = %s
              AND (last_used_at IS NULL OR last_used_at < now() - interval '5 minutes')
            """,
            (_hash_key(plain),),
        )
        conn.commit()
        return _row_to_user(row)


def list_api_keys(dsn: str, user_id: int) -> list[dict[str, Any]]:
    import psycopg
    from psycopg.rows import dict_row

    with psycopg.connect(dsn, row_factory=dict_row) as conn, conn.cursor() as cur:
        cur.execute(
            """
            SELECT id, key_prefix, name, created_at, last_used_at, expires_at, revoked_at
            FROM api_keys WHERE user_id = %s ORDER BY created_at DESC
            """,
            (user_id,),
        )
        return [
            {
                k: (v.isoformat() if isinstance(v, datetime) else v)
                for k, v in dict(row).items()
            }
            for row in cur.fetchall()
        ]


def revoke_api_key(dsn: str, *, user_id: int, key_id: int) -> bool:
    """Revoca una llave del propio usuario. Devuelve False si no era suya."""
    import psycopg

    with psycopg.connect(dsn) as conn, conn.cursor() as cur:
        cur.execute(
            """
            UPDATE api_keys SET revoked_at = now()
            WHERE id = %s AND user_id = %s AND revoked_at IS NULL
            """,
            (key_id, user_id),
        )
        revocadas = cur.rowcount
        conn.commit()
        return revocadas > 0


def revoke_all_api_keys(dsn: str, user_id: int) -> int:
    """Cerrar sesion en todos los dispositivos."""
    import psycopg

    with psycopg.connect(dsn) as conn, conn.cursor() as cur:
        cur.execute(
            "UPDATE api_keys SET revoked_at = now() WHERE user_id = %s AND revoked_at IS NULL",
            (user_id,),
        )
        total = cur.rowcount
        conn.commit()
        return total


# ---------------------------------------------------------------------------
# Consultas
# ---------------------------------------------------------------------------

_SELECT_USER = """
SELECT u.id, u.email, u.password_hash, u.full_name, u.org_id,
       u.is_superuser, u.is_active, o.slug AS org_slug
FROM users u
LEFT JOIN organizations o ON o.id = u.org_id
"""


def _row_to_user(row: dict[str, Any]) -> AuthUser:
    return AuthUser(
        id=row["id"],
        email=row["email"],
        org_id=row["org_id"],
        org_slug=row["org_slug"],
        is_superuser=row["is_superuser"],
        full_name=row["full_name"],
    )


def authenticate(dsn: str, email: str, password: str) -> AuthUser:
    """Verifica credenciales. Lanza AuthError si no son validas."""
    import psycopg
    from psycopg.rows import dict_row

    with psycopg.connect(dsn, row_factory=dict_row) as conn, conn.cursor() as cur:
        cur.execute(_SELECT_USER + " WHERE lower(u.email) = lower(%s)", (email,))
        row = cur.fetchone()

        if row is None:
            # Gastar el mismo tiempo que una verificacion real.
            verify_password(_DUMMY_HASH, password)
            raise AuthError("credenciales invalidas")

        if row["password_hash"] is None:
            # Cuenta que solo entra por Google. Mismo mensaje generico: decir
            # "esta cuenta usa Google" confirmaria que el correo existe.
            verify_password(_DUMMY_HASH, password)
            raise AuthError("credenciales invalidas")

        if not verify_password(row["password_hash"], password):
            raise AuthError("credenciales invalidas")

        if not row["is_active"]:
            # Mensaje distinto a proposito: la cuenta existe y es del usuario,
            # decirle que esta desactivada le ahorra soporte.
            raise AuthError("la cuenta esta desactivada")

        cur.execute("UPDATE users SET last_login_at = now() WHERE id = %s", (row["id"],))
        conn.commit()
        return _row_to_user(row)


def get_user(dsn: str, user_id: int) -> AuthUser | None:
    import psycopg
    from psycopg.rows import dict_row

    with psycopg.connect(dsn, row_factory=dict_row) as conn, conn.cursor() as cur:
        cur.execute(_SELECT_USER + " WHERE u.id = %s AND u.is_active", (user_id,))
        row = cur.fetchone()
        return _row_to_user(row) if row else None


def create_user(
    dsn: str,
    *,
    email: str,
    password: str | None = None,
    org_slug: str | None = None,
    is_superuser: bool = False,
    full_name: str | None = None,
) -> int:
    """Crea o actualiza un usuario. Idempotente por correo.

    Sin contrasena el usuario solo puede entrar por Google, que es el camino
    normal: el equipo no gestiona contrasenas de terceros.
    """
    import psycopg

    if not is_superuser and not org_slug:
        raise ValueError("un usuario que no es superusuario necesita organizacion")

    password_hash = hash_password(password) if password else None

    with psycopg.connect(dsn) as conn, conn.cursor() as cur:
        org_id = None
        if org_slug:
            cur.execute("SELECT id FROM organizations WHERE slug = %s", (org_slug,))
            found = cur.fetchone()
            if found is None:
                raise ValueError(f"la organizacion {org_slug!r} no existe")
            org_id = found[0]

        cur.execute(
            """
            INSERT INTO users (email, password_hash, full_name, org_id, is_superuser)
            VALUES (lower(%s), %s, %s, %s, %s)
            ON CONFLICT (lower(email)) DO UPDATE SET
              -- COALESCE: re-dar de alta sin contrasena no borra la que ya tenia.
              password_hash = COALESCE(EXCLUDED.password_hash, users.password_hash),
              full_name     = EXCLUDED.full_name,
              org_id        = EXCLUDED.org_id,
              is_superuser  = EXCLUDED.is_superuser,
              is_active     = true
            RETURNING id
            """,
            (email, password_hash, full_name, org_id, is_superuser),
        )
        user_id = require_row(cur.fetchone(), "crear usuario")[0]
        conn.commit()
        return user_id


def list_users(dsn: str) -> list[dict[str, Any]]:
    import psycopg
    from psycopg.rows import dict_row

    with psycopg.connect(dsn, row_factory=dict_row) as conn, conn.cursor() as cur:
        cur.execute(
            """
            SELECT u.email, u.full_name, u.is_superuser, u.is_active,
                   o.slug AS org, u.last_login_at
            FROM users u
            LEFT JOIN organizations o ON o.id = u.org_id
            ORDER BY u.is_superuser DESC, o.slug NULLS FIRST, u.email
            """
        )
        return [dict(row) for row in cur.fetchall()]


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    from fierro_api.settings import Settings

    parser = argparse.ArgumentParser(description="Crea o lista usuarios de la API.")
    parser.add_argument("--email")
    parser.add_argument("--org", help="Slug de la organizacion")
    parser.add_argument("--name", help="Nombre completo")
    parser.add_argument("--superuser", action="store_true", help="Ve todas las organizaciones")
    parser.add_argument(
        "--with-password",
        action="store_true",
        help="Pedir una contrasena de respaldo (por defecto: solo Google)",
    )
    parser.add_argument(
        "--password-stdin",
        action="store_true",
        help="Leer la contrasena de stdin en vez de preguntarla",
    )
    parser.add_argument("--list", action="store_true")
    args = parser.parse_args(argv)

    dsn = Settings.from_env().dsn
    if not dsn:
        print(
            "FIERRO_API_DSN no esta definido. Los usuarios requieren Postgres.",
            file=sys.stderr,
        )
        return 2

    if args.list:
        for row in list_users(dsn):
            marca = "superusuario" if row["is_superuser"] else (row["org"] or "-")
            estado = "" if row["is_active"] else "  (desactivado)"
            print(f"  {row['email']:<32} {marca:<16}{estado}")
        return 0

    if not args.email:
        print("Falta --email (o usa --list)", file=sys.stderr)
        return 2

    # Sin contrasena por defecto: el camino normal es Google. Y nunca por
    # argumento, que quedaria en el historial del shell y en `ps`.
    password = None
    if args.password_stdin:
        password = sys.stdin.readline().rstrip("\n")
    elif args.with_password:
        password = getpass.getpass("Contrasena: ")

    try:
        user_id = create_user(
            dsn,
            email=args.email,
            password=password,
            org_slug=args.org,
            is_superuser=args.superuser,
            full_name=args.name,
        )
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    alcance = "todas las organizaciones" if args.superuser else args.org
    via = "contrasena + Google" if password else "solo Google"
    print(f"usuario {args.email} listo (id {user_id}, alcance: {alcance}, entra por: {via})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
