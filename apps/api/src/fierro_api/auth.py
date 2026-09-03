"""Usuarios, contrasenas y tokens de acceso.

Decision tomada por el equipo: **JWT en localStorage**, no cookie de sesion.

Consecuencia asumida, escrita aqui para que nadie la descubra despues:
un XSS en la PWA puede leer el token, y no hay revocacion real — un token
robado sirve hasta que expira. Se mitiga con vida corta y claims minimos.
Cuando entre 2FA conviene reevaluarlo, porque 2FA sin poder cerrar sesiones
existentes protege menos de lo que parece.

Solo Postgres: el modo SQLite es de laboratorio y de un solo inquilino.
"""

from __future__ import annotations

import argparse
import getpass
import logging
import sys
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError

# argon2id con parametros por defecto de argon2-cffi, que siguen la
# recomendacion de OWASP. Subirlos es una decision de operacion, no de codigo.
_hasher = PasswordHasher()

# Hash desechable para gastar el mismo tiempo cuando el correo no existe.
# Sin esto, la diferencia de latencia revela que cuentas estan registradas.
_DUMMY_HASH = _hasher.hash("no-such-user-timing-guard")

ALGORITHM = "HS256"

logger = logging.getLogger(__name__)


class AuthError(Exception):
    """Credenciales invalidas o token no utilizable."""


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
# Contrasenas
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
# Tokens
# ---------------------------------------------------------------------------


def create_access_token(user: AuthUser, *, secret: str, ttl_minutes: int) -> tuple[str, int]:
    """Devuelve (token, segundos_de_vida).

    Los claims son minimos y publicos: cualquiera con el token los lee. Nada
    de nombre completo ni datos que no hagan falta para autorizar.
    """
    import jwt

    now = datetime.now(timezone.utc)
    expires = now + timedelta(minutes=ttl_minutes)
    claims = {
        "sub": str(user.id),
        "email": user.email,
        "org": user.org_slug,
        "su": user.is_superuser,
        "iat": int(now.timestamp()),
        "exp": int(expires.timestamp()),
    }
    return jwt.encode(claims, secret, algorithm=ALGORITHM), ttl_minutes * 60


def decode_access_token(token: str, *, secret: str) -> dict[str, Any]:
    import jwt

    try:
        # algorithms explicito: aceptar el del token permitiria el ataque
        # clasico de bajar el algoritmo a "none".
        return jwt.decode(token, secret, algorithms=[ALGORITHM])
    except jwt.ExpiredSignatureError as exc:
        raise AuthError("el token expiro") from exc
    except jwt.InvalidTokenError as exc:
        raise AuthError("token invalido") from exc


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
    password: str,
    org_slug: str | None = None,
    is_superuser: bool = False,
    full_name: str | None = None,
) -> int:
    """Crea o actualiza un usuario. Idempotente por correo."""
    import psycopg

    if not is_superuser and not org_slug:
        raise ValueError("un usuario que no es superusuario necesita organizacion")

    password_hash = hash_password(password)

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
              password_hash = EXCLUDED.password_hash,
              full_name     = EXCLUDED.full_name,
              org_id        = EXCLUDED.org_id,
              is_superuser  = EXCLUDED.is_superuser,
              is_active     = true
            RETURNING id
            """,
            (email, password_hash, full_name, org_id, is_superuser),
        )
        user_id = cur.fetchone()[0]
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

    # Nunca por argumento: quedaria en el historial del shell y en `ps`.
    if args.password_stdin:
        password = sys.stdin.readline().rstrip("\n")
    else:
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
    print(f"usuario {args.email} listo (id {user_id}, alcance: {alcance})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
