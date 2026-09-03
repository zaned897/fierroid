"""Verificacion de identidad con Google (OpenID Connect).

El equipo no gestiona contrasenas de terceros: Google prueba quien es la
persona, y nosotros emitimos una API key propia. Google nunca ve nuestros datos
ni nuestra sesion; solo confirma el correo.

**El acceso es por invitacion.** Tener cuenta de Google no da entrada: el correo
tiene que existir ya en `users`, creado por un administrador con su
organizacion. Si no, cualquiera con un Gmail entraria al sistema.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from jwt import PyJWKClient

    from fierro_api.auth import AuthUser

from fierro_api.auth import AuthError

logger = logging.getLogger(__name__)

# Google usa las dos formas historicamente; ambas son legitimas.
GOOGLE_ISSUERS = frozenset({"https://accounts.google.com", "accounts.google.com"})
GOOGLE_JWKS_URL = "https://www.googleapis.com/oauth2/v3/certs"

_jwks_client = None


@dataclass(frozen=True)
class GoogleIdentity:
    sub: str
    email: str
    name: str | None = None


def _default_jwks_client() -> "PyJWKClient":
    """Cliente JWKS compartido: cachea las llaves publicas de Google."""
    global _jwks_client
    if _jwks_client is None:
        from jwt import PyJWKClient

        _jwks_client = PyJWKClient(GOOGLE_JWKS_URL, cache_keys=True)
    return _jwks_client


def verify_id_token(token: str, *, client_id: str, jwks_client: Any = None) -> GoogleIdentity:
    """Valida un ID token de Google y devuelve la identidad que afirma.

    jwks_client es inyectable para poder probar esto sin llamar a Google.
    """
    import jwt

    if not client_id:
        raise AuthError("FIERRO_GOOGLE_CLIENT_ID no esta configurado")

    client = jwks_client or _default_jwks_client()
    try:
        signing_key = client.get_signing_key_from_jwt(token)
        claims = jwt.decode(
            token,
            signing_key.key,
            # Explicito: sin esto, un token firmado con HS256 usando la llave
            # publica de Google como secreto se aceptaria como valido.
            algorithms=["RS256"],
            # audience: el token tiene que haber sido emitido PARA esta app.
            # Sin esta comprobacion sirve un token de cualquier otra app Google.
            audience=client_id,
            options={"require": ["exp", "iat", "aud", "iss", "sub"]},
        )
    except jwt.PyJWTError as exc:
        raise AuthError(f"ID token de Google invalido: {exc}") from exc
    except Exception as exc:  # noqa: BLE001 - fallo de red al traer las JWKS
        raise AuthError(f"no se pudieron verificar las llaves de Google: {exc}") from exc

    if claims.get("iss") not in GOOGLE_ISSUERS:
        raise AuthError("el emisor del token no es Google")

    email = (claims.get("email") or "").strip()
    if not email:
        raise AuthError("el token de Google no trae correo")

    if not claims.get("email_verified"):
        # Sin esto, una cuenta con correo sin verificar podria reclamar la
        # direccion de otra persona.
        raise AuthError("el correo de la cuenta de Google no esta verificado")

    return GoogleIdentity(sub=claims["sub"], email=email, name=claims.get("name"))


def user_for_identity(dsn: str, identity: GoogleIdentity) -> "AuthUser":
    """Busca al usuario invitado que corresponde a esa identidad.

    No crea usuarios: el alta es por invitacion. Si el correo no esta dado de
    alta, no hay acceso.
    """
    import psycopg
    from psycopg.rows import dict_row

    from fierro_api.auth import _SELECT_USER, _row_to_user

    with psycopg.connect(dsn, row_factory=dict_row) as conn, conn.cursor() as cur:
        cur.execute(
            _SELECT_USER + " WHERE lower(u.email) = lower(%s) AND u.is_active",
            (identity.email,),
        )
        row = cur.fetchone()
        if row is None:
            logger.warning("intento de acceso de un correo no invitado")
            raise AuthError(
                "Esa cuenta no tiene acceso. Pide a un administrador que te de de alta."
            )

        # Se guarda el sub de Google la primera vez, para dejar rastro de como
        # entro cada quien. Solo si esta vacio: no se pisa uno ya vinculado.
        cur.execute(
            "UPDATE users SET google_sub = %s WHERE id = %s AND google_sub IS NULL",
            (identity.sub, row["id"]),
        )
        conn.commit()
        return _row_to_user(row)
