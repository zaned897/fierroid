"""Contrasenas, API keys e identidad de Google.

Los tokens de Google se firman aqui con un par de llaves RSA generado en la
prueba y un cliente JWKS falso: verificar identidad no debe depender de tener
red ni de llamar a Google.
"""

from __future__ import annotations

import json
import os
import uuid
from datetime import datetime, timedelta, timezone

import pytest
from fierro_api.auth import (
    KEY_PREFIX,
    AuthError,
    generate_api_key,
    hash_password,
    verify_password,
)
from fierro_api.google_auth import GOOGLE_JWKS_URL, GoogleIdentity, verify_id_token

DSN = os.getenv("FIERRO_TEST_PG_DSN", "").strip()
CLIENT_ID = "1234567890-prueba.apps.googleusercontent.com"


# ---------------------------------------------------------------------------
# Contrasenas
# ---------------------------------------------------------------------------


def test_hash_y_verificacion():
    stored = hash_password("contrasena-de-prueba")
    assert verify_password(stored, "contrasena-de-prueba")


def test_contrasena_incorrecta_no_verifica():
    assert not verify_password(hash_password("contrasena-de-prueba"), "otra-cosa")


def test_el_hash_nunca_contiene_la_contrasena():
    assert "contrasena-de-prueba" not in hash_password("contrasena-de-prueba")


def test_dos_hashes_de_lo_mismo_son_distintos():
    """Con sal: dos cuentas con la misma contrasena no se delatan entre si."""
    assert hash_password("misma-contrasena") != hash_password("misma-contrasena")


def test_contrasena_corta_se_rechaza():
    with pytest.raises(ValueError, match="8 caracteres"):
        hash_password("corta")


def test_hash_corrupto_no_revienta():
    """InvalidHashError hereda de ValueError: sin esa rama seria un 500."""
    assert not verify_password("esto-no-es-un-hash-argon2", "lo-que-sea")


# ---------------------------------------------------------------------------
# API keys
# ---------------------------------------------------------------------------


def test_la_llave_lleva_prefijo_reconocible():
    """Para identificarla de un vistazo si se filtra en un log o un repo."""
    plain, _, prefix = generate_api_key()
    assert plain.startswith(KEY_PREFIX)
    assert plain.startswith(prefix)


def test_el_hash_guardado_no_permite_reconstruir_la_llave():
    plain, key_hash, prefix = generate_api_key()
    assert plain not in key_hash
    assert len(key_hash) == 64  # sha256 en hexadecimal
    assert plain[len(prefix) :] not in key_hash


def test_dos_llaves_nunca_coinciden():
    llaves = {generate_api_key()[0] for _ in range(200)}
    assert len(llaves) == 200


# ---------------------------------------------------------------------------
# Identidad de Google, con JWKS falso
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def rsa_keys():
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric import rsa

    private = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    pem = private.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    return pem, private.public_key()


@pytest.fixture
def jwks(rsa_keys):
    """Cliente JWKS falso: devuelve siempre nuestra llave publica de prueba."""

    class FakeKey:
        def __init__(self, key):
            self.key = key

    class FakeClient:
        def __init__(self, key):
            self._key = FakeKey(key)

        def get_signing_key_from_jwt(self, token):  # noqa: ARG002
            return self._key

    return FakeClient(rsa_keys[1])


@pytest.fixture
def firmar(rsa_keys):
    import jwt

    def _firmar(**overrides):
        ahora = datetime.now(timezone.utc)
        claims = {
            "iss": "https://accounts.google.com",
            "aud": CLIENT_ID,
            "sub": "108123456789012345678",
            "email": "ana@los-encinos.mx",
            "email_verified": True,
            "name": "Ana Ruiz",
            "iat": int(ahora.timestamp()),
            "exp": int((ahora + timedelta(hours=1)).timestamp()),
        }
        claims.update(overrides)
        return jwt.encode(claims, rsa_keys[0], algorithm="RS256", headers={"kid": "prueba"})

    return _firmar


def test_token_valido_devuelve_la_identidad(firmar, jwks):
    identidad = verify_id_token(firmar(), client_id=CLIENT_ID, jwks_client=jwks)

    assert identidad == GoogleIdentity(
        sub="108123456789012345678", email="ana@los-encinos.mx", name="Ana Ruiz"
    )


def test_token_de_otra_app_se_rechaza(firmar, jwks):
    """Sin comprobar audience, sirve un token de cualquier otra app de Google."""
    token = firmar(aud="otra-app.apps.googleusercontent.com")
    with pytest.raises(AuthError):
        verify_id_token(token, client_id=CLIENT_ID, jwks_client=jwks)


def test_emisor_que_no_es_google_se_rechaza(firmar, jwks):
    with pytest.raises(AuthError, match="emisor"):
        verify_id_token(firmar(iss="https://accounts.malicioso.mx"), client_id=CLIENT_ID,
                        jwks_client=jwks)


def test_emisor_sin_esquema_es_valido(firmar, jwks):
    """Google emite las dos formas; ambas son legitimas."""
    identidad = verify_id_token(
        firmar(iss="accounts.google.com"), client_id=CLIENT_ID, jwks_client=jwks
    )
    assert identidad.email == "ana@los-encinos.mx"


def test_correo_sin_verificar_se_rechaza(firmar, jwks):
    """Si no, una cuenta podria reclamar la direccion de otra persona."""
    with pytest.raises(AuthError, match="no esta verificado"):
        verify_id_token(firmar(email_verified=False), client_id=CLIENT_ID, jwks_client=jwks)


def test_token_sin_correo_se_rechaza(firmar, jwks):
    with pytest.raises(AuthError, match="correo"):
        verify_id_token(firmar(email=""), client_id=CLIENT_ID, jwks_client=jwks)


def test_token_expirado_se_rechaza(firmar, jwks):
    ayer = datetime.now(timezone.utc) - timedelta(days=1)
    token = firmar(exp=int(ayer.timestamp()), iat=int((ayer - timedelta(hours=1)).timestamp()))
    with pytest.raises(AuthError):
        verify_id_token(token, client_id=CLIENT_ID, jwks_client=jwks)


def test_confusion_de_algoritmo_se_rechaza(rsa_keys, jwks):
    """El ataque clasico: firmar con HS256 usando la llave PUBLICA como secreto.

    Si el verificador no fija el algoritmo, acepta ese token porque la llave
    publica de Google es, justamente, publica.

    El token se forja a mano con hmac y no con jwt.encode() a proposito: PyJWT
    se niega a firmar HMAC con una llave PEM, pero un atacante no usa PyJWT.
    """
    import base64
    import hashlib
    import hmac

    from cryptography.hazmat.primitives import serialization

    publica = rsa_keys[1].public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )

    def b64(raw: bytes) -> str:
        return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()

    ahora = datetime.now(timezone.utc)
    cabecera = b64(json.dumps({"alg": "HS256", "typ": "JWT", "kid": "prueba"}).encode())
    cuerpo = b64(
        json.dumps(
            {
                "iss": "https://accounts.google.com",
                "aud": CLIENT_ID,
                "sub": "1",
                "email": "atacante@mal.mx",
                "email_verified": True,
                "iat": int(ahora.timestamp()),
                "exp": int((ahora + timedelta(hours=1)).timestamp()),
            }
        ).encode()
    )
    firmado = f"{cabecera}.{cuerpo}".encode()
    firma = b64(hmac.new(publica, firmado, hashlib.sha256).digest())

    with pytest.raises(AuthError):
        verify_id_token(f"{cabecera}.{cuerpo}.{firma}", client_id=CLIENT_ID, jwks_client=jwks)


def test_sin_client_id_configurado_falla_claro(firmar, jwks):
    with pytest.raises(AuthError, match="FIERRO_GOOGLE_CLIENT_ID"):
        verify_id_token(firmar(), client_id="", jwks_client=jwks)


def test_la_url_de_jwks_es_la_de_google():
    assert GOOGLE_JWKS_URL.startswith("https://www.googleapis.com/")


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


@pytest.fixture
def usuario(migrated, correo, limpiar):
    """Usuario invitado de los-encinos, con contrasena de respaldo."""
    from fierro_api.auth import create_user

    limpiar.append(correo)
    user_id = create_user(
        migrated,
        email=correo,
        password="clave-de-prueba",
        org_slug="los-encinos",
        full_name="Ana Ruiz",
    )
    return user_id, correo


@pg
def test_llave_emitida_resuelve_al_usuario(migrated, usuario):
    from fierro_api.auth import issue_api_key, user_for_api_key

    user_id, correo = usuario
    emitida = issue_api_key(migrated, user_id=user_id, name="prueba")

    user = user_for_api_key(migrated, emitida["api_key"])
    assert user is not None
    assert user.email == correo
    assert user.org_slug == "los-encinos"


@pg
def test_llave_inventada_no_resuelve(migrated):
    from fierro_api.auth import user_for_api_key

    assert user_for_api_key(migrated, "fierro_llave-que-no-existe") is None


@pg
def test_llave_revocada_deja_de_servir(migrated, usuario):
    from fierro_api.auth import issue_api_key, revoke_api_key, user_for_api_key

    user_id, _ = usuario
    emitida = issue_api_key(migrated, user_id=user_id)
    assert user_for_api_key(migrated, emitida["api_key"]) is not None

    assert revoke_api_key(migrated, user_id=user_id, key_id=emitida["id"]) is True
    assert user_for_api_key(migrated, emitida["api_key"]) is None


@pg
def test_llave_expirada_deja_de_servir(migrated, usuario):
    import psycopg
    from fierro_api.auth import issue_api_key, user_for_api_key

    user_id, _ = usuario
    emitida = issue_api_key(migrated, user_id=user_id)
    with psycopg.connect(migrated) as conn, conn.cursor() as cur:
        cur.execute(
            "UPDATE api_keys SET expires_at = now() - interval '1 day' WHERE id = %s",
            (emitida["id"],),
        )
        conn.commit()

    assert user_for_api_key(migrated, emitida["api_key"]) is None


@pg
def test_llave_sin_expiracion_se_puede_emitir(migrated, usuario):
    from fierro_api.auth import issue_api_key, user_for_api_key

    user_id, _ = usuario
    emitida = issue_api_key(migrated, user_id=user_id, ttl_days=None)

    assert emitida["expires_at"] is None
    assert user_for_api_key(migrated, emitida["api_key"]) is not None


@pg
def test_no_se_revocan_llaves_ajenas(migrated, usuario, limpiar):
    from fierro_api.auth import create_user, issue_api_key, revoke_api_key, user_for_api_key

    user_id, _ = usuario
    ajeno = f"otro-{uuid.uuid4().hex[:8]}@fierro.test"
    limpiar.append(ajeno)
    otro_id = create_user(
        migrated, email=ajeno, password="clave-de-prueba", org_slug="valle-verde"
    )
    emitida = issue_api_key(migrated, user_id=otro_id)

    assert revoke_api_key(migrated, user_id=user_id, key_id=emitida["id"]) is False
    assert user_for_api_key(migrated, emitida["api_key"]) is not None


@pg
def test_cerrar_sesion_en_todos_los_dispositivos(migrated, usuario):
    from fierro_api.auth import issue_api_key, revoke_all_api_keys, user_for_api_key

    user_id, _ = usuario
    llaves = [issue_api_key(migrated, user_id=user_id)["api_key"] for _ in range(3)]

    assert revoke_all_api_keys(migrated, user_id) == 3
    assert all(user_for_api_key(migrated, k) is None for k in llaves)


@pg
def test_el_listado_nunca_expone_la_llave(migrated, usuario):
    from fierro_api.auth import issue_api_key, list_api_keys

    user_id, _ = usuario
    emitida = issue_api_key(migrated, user_id=user_id, name="telefono")

    listado = list_api_keys(migrated, user_id)
    assert emitida["api_key"] not in json.dumps(listado)
    assert any(k["key_prefix"] == emitida["key_prefix"] for k in listado)


@pg
def test_usuario_solo_google_no_entra_con_contrasena(migrated, correo, limpiar):
    """password_hash es NULL: no debe reventar, debe rechazar igual que siempre."""
    import psycopg
    from fierro_api.auth import authenticate, create_user

    limpiar.append(correo)
    create_user(migrated, email=correo, password="clave-de-prueba", org_slug="los-encinos")
    with psycopg.connect(migrated) as conn, conn.cursor() as cur:
        cur.execute("UPDATE users SET password_hash = NULL WHERE lower(email) = lower(%s)",
                    (correo,))
        conn.commit()

    with pytest.raises(AuthError, match="credenciales"):
        authenticate(migrated, correo, "clave-de-prueba")


@pg
def test_google_solo_deja_entrar_a_invitados(migrated, usuario):
    from fierro_api.google_auth import user_for_identity

    _, correo = usuario
    user = user_for_identity(migrated, GoogleIdentity(sub="sub-1", email=correo))
    assert user.email == correo

    with pytest.raises(AuthError, match="no tiene acceso"):
        user_for_identity(migrated, GoogleIdentity(sub="sub-2", email="ajeno@gmail.com"))


@pg
def test_google_guarda_el_sub_la_primera_vez(migrated, usuario):
    import psycopg
    from fierro_api.google_auth import user_for_identity

    user_id, correo = usuario
    user_for_identity(migrated, GoogleIdentity(sub="sub-original", email=correo))
    user_for_identity(migrated, GoogleIdentity(sub="sub-distinto", email=correo))

    with psycopg.connect(migrated) as conn, conn.cursor() as cur:
        cur.execute("SELECT google_sub FROM users WHERE id = %s", (user_id,))
        # No se pisa un vinculo ya establecido.
        assert cur.fetchone()[0] == "sub-original"


@pg
def test_usuario_sin_contrasena_solo_entra_por_google(migrated, correo, limpiar):
    """El camino normal: nadie gestiona contrasenas de terceros."""
    import psycopg
    from fierro_api.auth import authenticate, create_user
    from fierro_api.google_auth import user_for_identity

    limpiar.append(correo)
    create_user(migrated, email=correo, org_slug="los-encinos")

    with psycopg.connect(migrated) as conn, conn.cursor() as cur:
        cur.execute("SELECT password_hash FROM users WHERE lower(email) = lower(%s)", (correo,))
        assert cur.fetchone()[0] is None

    with pytest.raises(AuthError, match="credenciales"):
        authenticate(migrated, correo, "cualquier-cosa")

    assert user_for_identity(migrated, GoogleIdentity(sub="s", email=correo)).email == correo


@pg
def test_redar_de_alta_sin_contrasena_no_borra_la_existente(migrated, correo, limpiar):
    from fierro_api.auth import authenticate, create_user

    limpiar.append(correo)
    create_user(migrated, email=correo, password="clave-de-prueba", org_slug="los-encinos")
    create_user(migrated, email=correo, org_slug="valle-verde", full_name="Ana")

    user = authenticate(migrated, correo, "clave-de-prueba")
    assert user.org_slug == "valle-verde"


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@pytest.fixture
def client(migrated, monkeypatch):
    from dataclasses import replace

    from fastapi.testclient import TestClient
    from fierro_api import main as main_module

    monkeypatch.setattr(
        main_module,
        "settings",
        replace(main_module.settings, dsn=migrated, google_client_id=CLIENT_ID),
    )
    return TestClient(main_module.app)


@pg
def test_login_devuelve_api_key(client, usuario):
    _, correo = usuario
    resp = client.post("/v1/auth/login", json={"email": correo, "password": "clave-de-prueba"})

    assert resp.status_code == 200
    body = resp.json()
    assert body["api_key"].startswith(KEY_PREFIX)
    assert body["user"]["org"] == "los-encinos"
    assert body["expires_at"] is not None


@pg
def test_la_api_key_abre_me(client, usuario):
    _, correo = usuario
    key = client.post(
        "/v1/auth/login", json={"email": correo, "password": "clave-de-prueba"}
    ).json()["api_key"]

    resp = client.get("/v1/auth/me", headers={"Authorization": f"Bearer {key}"})
    assert resp.status_code == 200
    assert resp.json()["email"] == correo


@pg
def test_revocar_la_llave_corta_el_acceso_de_inmediato(client, usuario):
    """La razon de ser de la API key frente a un JWT."""
    _, correo = usuario
    sesion = client.post(
        "/v1/auth/login", json={"email": correo, "password": "clave-de-prueba"}
    ).json()
    cabeceras = {"Authorization": f"Bearer {sesion['api_key']}"}

    assert client.get("/v1/auth/me", headers=cabeceras).status_code == 200

    borrado = client.delete(f"/v1/auth/keys/{sesion['id']}", headers=cabeceras)
    assert borrado.status_code == 200

    assert client.get("/v1/auth/me", headers=cabeceras).status_code == 401


@pg
def test_logout_all_cierra_todas(client, usuario):
    _, correo = usuario
    primera = client.post(
        "/v1/auth/login", json={"email": correo, "password": "clave-de-prueba"}
    ).json()["api_key"]
    segunda = client.post(
        "/v1/auth/login", json={"email": correo, "password": "clave-de-prueba"}
    ).json()["api_key"]

    resp = client.post("/v1/auth/logout-all", headers={"Authorization": f"Bearer {primera}"})
    assert resp.status_code == 200

    for key in (primera, segunda):
        cabeceras = {"Authorization": f"Bearer {key}"}
        assert client.get("/v1/auth/me", headers=cabeceras).status_code == 401


@pg
def test_me_sin_credencial_da_401(client):
    assert client.get("/v1/auth/me").status_code == 401
    assert client.get(
        "/v1/auth/me", headers={"Authorization": "Bearer no-es-una-llave"}
    ).status_code == 401


@pg
def test_google_sin_configurar_da_503(migrated, monkeypatch):
    from dataclasses import replace

    from fastapi.testclient import TestClient
    from fierro_api import main as main_module

    monkeypatch.setattr(
        main_module,
        "settings",
        replace(main_module.settings, dsn=migrated, google_client_id=""),
    )
    resp = TestClient(main_module.app).post("/v1/auth/google", json={"id_token": "lo-que-sea"})

    assert resp.status_code == 503
    assert "FIERRO_GOOGLE_CLIENT_ID" in resp.json()["detail"]


@pg
def test_google_con_token_invalido_da_401(client):
    resp = client.post("/v1/auth/google", json={"id_token": "esto.no.es"})
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Configuracion publica
# ---------------------------------------------------------------------------


@pg
def test_config_expone_el_client_id(client):
    """La PWA lo pide en tiempo de ejecucion en vez de recibirlo del build."""
    resp = client.get("/v1/auth/config")

    assert resp.status_code == 200
    body = resp.json()
    assert body["google_client_id"] == CLIENT_ID
    assert body["google_enabled"] is True
    assert body["env"] == "dev"
    assert body["providers"] == [{"id": "google", "name": "Google"}]


@pg
def test_config_no_exige_credencial(client):
    """Se consulta antes de que nadie haya entrado; pedir credencial seria un ciclo."""
    assert "authorization" not in {k.lower() for k in client.headers}
    assert client.get("/v1/auth/config").status_code == 200


@pg
def test_config_no_filtra_nada_secreto(client):
    """El client ID es publico; el DSN y el secreto de OAuth no deben asomarse."""
    crudo = json.dumps(client.get("/v1/auth/config").json())

    assert "postgresql://" not in crudo
    assert "password" not in crudo.lower()
    assert set(json.loads(crudo)) == {"providers", "google_client_id", "google_enabled", "env"}


@pg
def test_config_avisa_cuando_google_no_esta_configurado(migrated, monkeypatch):
    """google_enabled es lo que la PWA usa para explicar por que no hay boton."""
    from dataclasses import replace

    from fastapi.testclient import TestClient
    from fierro_api import main as main_module

    monkeypatch.setattr(
        main_module, "settings", replace(main_module.settings, dsn=migrated, google_client_id="")
    )
    body = TestClient(main_module.app).get("/v1/auth/config").json()

    assert body["google_client_id"] == ""
    assert body["google_enabled"] is False
    # Sin configurar, no se anuncia: un boton que falla es peor que ninguno.
    assert body["providers"] == []
