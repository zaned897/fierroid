"""Contrasenas, tokens y login.

Las pruebas de criptografia corren siempre; las de base y endpoints requieren
FIERRO_TEST_PG_DSN.
"""

from __future__ import annotations

import base64
import json
import os
import uuid
from datetime import datetime, timedelta, timezone

import pytest
from fierro_api.auth import (
    ALGORITHM,
    AuthError,
    AuthUser,
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)

DSN = os.getenv("FIERRO_TEST_PG_DSN", "").strip()
SECRETO = "secreto-de-pruebas-suficientemente-largo-1234"

USUARIO = AuthUser(
    id=7,
    email="ana@los-encinos.mx",
    org_id=1,
    org_slug="los-encinos",
    is_superuser=False,
    full_name="Ana Ruiz",
)


# ---------------------------------------------------------------------------
# Contrasenas
# ---------------------------------------------------------------------------


def test_hash_y_verificacion():
    stored = hash_password("contrasena-de-prueba")
    assert verify_password(stored, "contrasena-de-prueba")


def test_contrasena_incorrecta_no_verifica():
    stored = hash_password("contrasena-de-prueba")
    assert not verify_password(stored, "otra-cosa")


def test_el_hash_nunca_contiene_la_contrasena():
    stored = hash_password("contrasena-de-prueba")
    assert "contrasena-de-prueba" not in stored


def test_dos_hashes_de_lo_mismo_son_distintos():
    """Con sal: dos cuentas con la misma contrasena no se delatan entre si."""
    assert hash_password("misma-contrasena") != hash_password("misma-contrasena")


def test_contrasena_corta_se_rechaza():
    with pytest.raises(ValueError, match="8 caracteres"):
        hash_password("corta")


def test_hash_corrupto_no_revienta():
    """Una fila danada devuelve False, no una excepcion sin manejar."""
    assert not verify_password("esto-no-es-un-hash-argon2", "lo-que-sea")


# ---------------------------------------------------------------------------
# Tokens
# ---------------------------------------------------------------------------


def test_ida_y_vuelta_del_token():
    token, expires_in = create_access_token(USUARIO, secret=SECRETO, ttl_minutes=60)
    claims = decode_access_token(token, secret=SECRETO)

    assert claims["sub"] == "7"
    assert claims["org"] == "los-encinos"
    assert claims["su"] is False
    assert expires_in == 3600


def test_el_token_no_lleva_datos_de_mas():
    """Los claims los lee cualquiera que tenga el token: solo lo indispensable."""
    token, _ = create_access_token(USUARIO, secret=SECRETO, ttl_minutes=60)
    claims = decode_access_token(token, secret=SECRETO)

    assert set(claims) == {"sub", "email", "org", "su", "iat", "exp"}
    assert "Ana Ruiz" not in json.dumps(claims)


def test_token_con_otro_secreto_se_rechaza():
    token, _ = create_access_token(USUARIO, secret=SECRETO, ttl_minutes=60)
    with pytest.raises(AuthError):
        decode_access_token(token, secret="otro-secreto-igualmente-largo-000000")


def test_token_alterado_se_rechaza():
    token, _ = create_access_token(USUARIO, secret=SECRETO, ttl_minutes=60)
    cabecera, cuerpo, firma = token.split(".")
    alterado = f"{cabecera}.{cuerpo[:-4]}AAAA.{firma}"
    with pytest.raises(AuthError):
        decode_access_token(alterado, secret=SECRETO)


def test_token_expirado_se_rechaza():
    token, _ = create_access_token(USUARIO, secret=SECRETO, ttl_minutes=-1)
    with pytest.raises(AuthError, match="expiro"):
        decode_access_token(token, secret=SECRETO)


def test_algoritmo_none_se_rechaza():
    """El ataque clasico: firmar con alg=none y que el servidor lo acepte."""

    def b64(data: dict) -> str:
        crudo = json.dumps(data, separators=(",", ":")).encode()
        return base64.urlsafe_b64encode(crudo).rstrip(b"=").decode()

    expira = int((datetime.now(timezone.utc) + timedelta(hours=1)).timestamp())
    falso = (
        b64({"alg": "none", "typ": "JWT"})
        + "."
        + b64({"sub": "1", "email": "atacante@mal.mx", "org": None, "su": True, "exp": expira})
        + "."
    )
    with pytest.raises(AuthError):
        decode_access_token(falso, secret=SECRETO)


def test_algoritmo_declarado_es_hmac():
    assert ALGORITHM == "HS256"


# ---------------------------------------------------------------------------
# Base de datos
# ---------------------------------------------------------------------------

pg = pytest.mark.skipif(not DSN, reason="FIERRO_TEST_PG_DSN no definido")


@pytest.fixture(scope="module")
def migrated():
    from fierro_api.migrate import apply_migrations
    from fierro_api.tenancy import build_specs, seed_tenants

    apply_migrations(DSN)
    seed_tenants(DSN, build_specs(orgs=2, ranches_per_org=1, devices_per_ranch=1))
    return DSN


@pytest.fixture
def correo():
    return f"prueba-{uuid.uuid4().hex[:10]}@fierro.test"


@pytest.fixture
def limpiar(migrated):
    creados: list[str] = []
    yield creados
    import psycopg

    with psycopg.connect(migrated) as conn, conn.cursor() as cur:
        for email in creados:
            cur.execute("DELETE FROM users WHERE lower(email) = lower(%s)", (email,))
        conn.commit()


@pg
def test_crear_usuario_y_autenticar(migrated, correo, limpiar):
    from fierro_api.auth import authenticate, create_user

    limpiar.append(correo)
    create_user(migrated, email=correo, password="clave-de-prueba", org_slug="los-encinos")

    user = authenticate(migrated, correo, "clave-de-prueba")
    assert user.email == correo
    assert user.org_slug == "los-encinos"
    assert user.is_superuser is False


@pg
def test_el_correo_no_distingue_mayusculas(migrated, correo, limpiar):
    from fierro_api.auth import authenticate, create_user

    limpiar.append(correo)
    create_user(migrated, email=correo, password="clave-de-prueba", org_slug="los-encinos")

    assert authenticate(migrated, correo.upper(), "clave-de-prueba").email == correo


@pg
def test_contrasena_incorrecta_no_autentica(migrated, correo, limpiar):
    from fierro_api.auth import authenticate, create_user

    limpiar.append(correo)
    create_user(migrated, email=correo, password="clave-de-prueba", org_slug="los-encinos")

    with pytest.raises(AuthError, match="credenciales"):
        authenticate(migrated, correo, "clave-equivocada")


@pg
def test_usuario_inexistente_da_el_mismo_error(migrated):
    """No revelar que correos estan registrados."""
    from fierro_api.auth import authenticate

    with pytest.raises(AuthError, match="credenciales"):
        authenticate(migrated, "nadie@fierro.test", "lo-que-sea")


@pg
def test_usuario_desactivado_no_entra(migrated, correo, limpiar):
    import psycopg
    from fierro_api.auth import authenticate, create_user

    limpiar.append(correo)
    create_user(migrated, email=correo, password="clave-de-prueba", org_slug="los-encinos")
    with psycopg.connect(migrated) as conn, conn.cursor() as cur:
        cur.execute("UPDATE users SET is_active = false WHERE lower(email) = lower(%s)", (correo,))
        conn.commit()

    with pytest.raises(AuthError, match="desactivada"):
        authenticate(migrated, correo, "clave-de-prueba")


@pg
def test_superusuario_no_necesita_organizacion(migrated, correo, limpiar):
    from fierro_api.auth import authenticate, create_user

    limpiar.append(correo)
    create_user(migrated, email=correo, password="clave-de-prueba", is_superuser=True)

    user = authenticate(migrated, correo, "clave-de-prueba")
    assert user.is_superuser is True
    assert user.org_slug is None


@pg
def test_usuario_normal_sin_organizacion_se_rechaza(migrated, correo):
    """Un usuario sin organizacion no veria nada, o peor, lo veria todo."""
    from fierro_api.auth import create_user

    with pytest.raises(ValueError, match="organizacion"):
        create_user(migrated, email=correo, password="clave-de-prueba")


@pg
def test_organizacion_inexistente_se_rechaza(migrated, correo):
    from fierro_api.auth import create_user

    with pytest.raises(ValueError, match="no existe"):
        create_user(migrated, email=correo, password="clave-de-prueba", org_slug="no-existe")


@pg
def test_crear_dos_veces_actualiza_en_vez_de_duplicar(migrated, correo, limpiar):
    from fierro_api.auth import authenticate, create_user

    limpiar.append(correo)
    primero = create_user(
        migrated, email=correo, password="clave-de-prueba", org_slug="los-encinos"
    )
    segundo = create_user(
        migrated, email=correo, password="clave-nueva-distinta", org_slug="valle-verde"
    )

    assert primero == segundo
    user = authenticate(migrated, correo, "clave-nueva-distinta")
    assert user.org_slug == "valle-verde"


@pg
def test_se_registra_el_ultimo_acceso(migrated, correo, limpiar):
    import psycopg
    from fierro_api.auth import authenticate, create_user

    limpiar.append(correo)
    create_user(migrated, email=correo, password="clave-de-prueba", org_slug="los-encinos")
    authenticate(migrated, correo, "clave-de-prueba")

    with psycopg.connect(migrated) as conn, conn.cursor() as cur:
        cur.execute("SELECT last_login_at FROM users WHERE lower(email) = lower(%s)", (correo,))
        assert cur.fetchone()[0] is not None


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@pytest.fixture
def client(migrated, monkeypatch):
    """App apuntando a Postgres, con secreto conocido."""
    from dataclasses import replace

    from fastapi.testclient import TestClient
    from fierro_api import main as main_module

    monkeypatch.setattr(
        main_module,
        "settings",
        replace(main_module.settings, dsn=migrated, jwt_secret=SECRETO, jwt_ttl_minutes=60),
    )
    return TestClient(main_module.app)


@pg
def test_login_devuelve_token_y_usuario(client, migrated, correo, limpiar):
    from fierro_api.auth import create_user

    limpiar.append(correo)
    create_user(migrated, email=correo, password="clave-de-prueba", org_slug="los-encinos")

    resp = client.post("/v1/auth/login", json={"email": correo, "password": "clave-de-prueba"})
    assert resp.status_code == 200

    body = resp.json()
    assert body["token_type"] == "bearer"
    assert body["expires_in"] == 3600
    assert body["user"]["org"] == "los-encinos"
    # La respuesta nunca devuelve el hash.
    assert "password" not in json.dumps(body)


@pg
def test_login_con_credenciales_malas_da_401(client, migrated, correo, limpiar):
    from fierro_api.auth import create_user

    limpiar.append(correo)
    create_user(migrated, email=correo, password="clave-de-prueba", org_slug="los-encinos")

    resp = client.post("/v1/auth/login", json={"email": correo, "password": "mala"})
    assert resp.status_code == 401


@pg
def test_me_requiere_token(client):
    assert client.get("/v1/auth/me").status_code == 401


@pg
def test_me_rechaza_token_basura(client):
    resp = client.get("/v1/auth/me", headers={"Authorization": "Bearer no-es-un-token"})
    assert resp.status_code == 401


@pg
def test_me_devuelve_al_usuario_del_token(client, migrated, correo, limpiar):
    from fierro_api.auth import create_user

    limpiar.append(correo)
    create_user(
        migrated,
        email=correo,
        password="clave-de-prueba",
        org_slug="los-encinos",
        full_name="Ana Ruiz",
    )

    login = client.post("/v1/auth/login", json={"email": correo, "password": "clave-de-prueba"})
    token = login.json()["access_token"]

    resp = client.get("/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert resp.json() == {
        "id": login.json()["user"]["id"],
        "email": correo,
        "full_name": "Ana Ruiz",
        "org": "los-encinos",
        "is_superuser": False,
    }


@pg
def test_desactivar_al_usuario_invalida_su_token(client, migrated, correo, limpiar):
    """La unica revocacion que existe con JWT: releer al usuario en cada request."""
    import psycopg
    from fierro_api.auth import create_user

    limpiar.append(correo)
    create_user(migrated, email=correo, password="clave-de-prueba", org_slug="los-encinos")
    login = client.post("/v1/auth/login", json={"email": correo, "password": "clave-de-prueba"})
    token = login.json()["access_token"]
    cabeceras = {"Authorization": f"Bearer {token}"}

    assert client.get("/v1/auth/me", headers=cabeceras).status_code == 200

    with psycopg.connect(migrated) as conn, conn.cursor() as cur:
        cur.execute("UPDATE users SET is_active = false WHERE lower(email) = lower(%s)", (correo,))
        conn.commit()

    assert client.get("/v1/auth/me", headers=cabeceras).status_code == 401
