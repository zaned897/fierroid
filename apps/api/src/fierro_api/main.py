from __future__ import annotations

import base64
from typing import Annotated, Any

from fastapi import Depends, FastAPI, File, HTTPException, Query, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field

from fierro_api import __version__, google_auth
from fierro_api import animals as animals_mod
from fierro_api.auth import (
    AuthError,
    AuthUser,
    authenticate,
    issue_api_key,
    list_api_keys,
    revoke_all_api_keys,
    revoke_api_key,
    user_for_api_key,
)
from fierro_api.settings import Settings
from fierro_api.store import build_store

settings = Settings.from_env()
# Antes de tocar la base: en stage o production, una config incompleta aborta
# el arranque en vez de degradar a un almacenamiento efimero.
settings.validate()
store = build_store(dsn=settings.dsn, db_path=settings.db_path)

app = FastAPI(title="Fierro API", version=__version__)
app.add_middleware(
    CORSMiddleware,
    allow_origins=list(settings.cors_origins),
    allow_methods=["*"],
    allow_headers=["*"],
)


class WeightReadingIn(BaseModel):
    event_id: str
    device_id: str
    tag_id: str
    weight_kg: float
    captured_at: str
    stable: bool = True
    source: str = "unknown"


class ReadingsBatchIn(BaseModel):
    readings: list[WeightReadingIn] = Field(default_factory=list)


class LoginIn(BaseModel):
    email: str
    password: str


class GoogleLoginIn(BaseModel):
    id_token: str


class AnimalIn(BaseModel):
    alias: str | None = None
    notes: str | None = None


class HeartbeatIn(BaseModel):
    pending_count: int = 0
    agent_version: str | None = None
    uptime_s: int | None = None


@app.get("/health")
def health() -> dict[str, Any]:
    # El entorno viaja en /health: es como el despliegue confirma que la
    # imagen que corre es la que se esperaba.
    return {"ok": True, "version": __version__, "env": settings.env}


# ---------------------------------------------------------------------------
# Autenticacion
# ---------------------------------------------------------------------------

bearer = HTTPBearer(auto_error=False)

# Annotated en vez de Depends() como default: es el estilo recomendado de
# FastAPI y evita el B008 de ruff.
BearerCreds = Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)]


def _require_postgres() -> str:
    """Los usuarios viven solo en Postgres; SQLite es laboratorio de un inquilino."""
    if not settings.dsn:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="La autenticacion requiere Postgres. Define FIERRO_API_DSN.",
        )
    return settings.dsn


def _session_response(dsn: str, user: AuthUser, origen: str) -> dict[str, Any]:
    """Emite la API key. La version en claro se devuelve UNA sola vez."""
    key = issue_api_key(
        dsn,
        user_id=user.id,
        name=origen,
        ttl_days=settings.api_key_ttl_days or None,
    )
    return {**key, "token_type": "bearer", "user": user.to_public()}


@app.get("/v1/auth/config")
def auth_config() -> dict[str, Any]:
    """Configuracion publica que la PWA necesita antes de que alguien entre.

    El client ID de OAuth es publico por diseno: viaja en el bundle de
    cualquier app con Google Sign-In. Servirlo desde aqui, en vez de inyectarlo
    al construir el front, deja una sola fuente de verdad y hace que cambiarlo
    no requiera reconstruir ni redesplegar la PWA.
    """
    return {
        "google_client_id": settings.google_client_id,
        "google_enabled": bool(settings.google_client_id and settings.dsn),
        "env": settings.env,
    }


@app.post("/v1/auth/google")
def login_google(body: GoogleLoginIn) -> dict[str, Any]:
    """Cambia un ID token de Google por una API key nuestra.

    Google solo confirma el correo. El alta es por invitacion: si ese correo no
    esta dado de alta, no hay acceso aunque la cuenta de Google sea valida.
    """
    dsn = _require_postgres()
    if not settings.google_client_id:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="El inicio de sesion con Google no esta configurado "
            "(falta FIERRO_GOOGLE_CLIENT_ID).",
        )

    try:
        identity = google_auth.verify_id_token(
            body.id_token, client_id=settings.google_client_id
        )
        user = google_auth.user_for_identity(dsn, identity)
    except AuthError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)
        ) from exc

    return _session_response(dsn, user, "google")


@app.post("/v1/auth/login")
def login(body: LoginIn) -> dict[str, Any]:
    """Via de respaldo con contrasena, para cuentas administrativas.

    El camino normal de las personas es /v1/auth/google.
    """
    dsn = _require_postgres()
    try:
        # argon2 tarda ~50-100 ms a proposito: es el freno natural a la fuerza
        # bruta mientras no haya limitacion de intentos.
        user = authenticate(dsn, body.email, body.password)
    except AuthError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)
        ) from exc

    return _session_response(dsn, user, "contrasena")


# Usuario sintetico del modo laboratorio. Existe para que el flujo
# hello-world del README siga funcionando sin Postgres ni usuarios.
#
# Es seguro porque settings.validate() prohibe SQLite en stage y production:
# un entorno desplegado no puede caer aqui por accidente.
LAB_USER = AuthUser(
    id=0,
    email="laboratorio@local",
    org_id=None,
    org_slug=None,
    is_superuser=True,
    full_name="Modo laboratorio",
)


def current_user(creds: BearerCreds) -> AuthUser:
    if not settings.dsn:
        # SQLite: sin tablas de usuarios ni de organizaciones. Exigir
        # credencial aqui solo romperia el laboratorio sin proteger nada,
        # porque tampoco hay varios inquilinos que separar.
        return LAB_USER

    if creds is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Falta el encabezado Authorization",
        )
    dsn = _require_postgres()

    # La llave se resuelve contra la base en cada request. Eso es lo que hace
    # que revocarla surta efecto de inmediato.
    user = user_for_api_key(dsn, creds.credentials)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credencial invalida, revocada o expirada",
        )
    return user


CurrentUser = Annotated[AuthUser, Depends(current_user)]


@app.get("/v1/auth/me")
def me(user: CurrentUser) -> dict[str, Any]:
    return user.to_public()


@app.get("/v1/auth/keys")
def get_keys(user: CurrentUser) -> dict[str, Any]:
    """Sesiones abiertas. Nunca devuelve la llave, solo su prefijo."""
    return {"keys": list_api_keys(_require_postgres(), user.id)}


@app.delete("/v1/auth/keys/{key_id}")
def delete_key(key_id: int, user: CurrentUser) -> dict[str, Any]:
    # Acotado al propio usuario: nadie revoca sesiones ajenas por id.
    if not revoke_api_key(_require_postgres(), user_id=user.id, key_id=key_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Esa credencial no existe o ya estaba revocada",
        )
    return {"ok": True, "revoked": key_id}


@app.post("/v1/auth/logout-all")
def logout_all(user: CurrentUser) -> dict[str, Any]:
    """Cerrar sesion en todos los dispositivos, la actual incluida."""
    return {"ok": True, "revoked": revoke_all_api_keys(_require_postgres(), user.id)}


# ---------------------------------------------------------------------------
# Alcance por organizacion
# ---------------------------------------------------------------------------


def _scope(user: AuthUser) -> str | None:
    """Organizacion a la que se acota la consulta. None = sin restringir.

    Solo el superusuario recibe None. Un usuario normal sin organizacion
    seria un None accidental, es decir acceso total: eso se corta aqui con un
    403. No ver nada es infinitamente mejor que verlo todo.
    """
    if user.is_superuser:
        return None
    if not user.org_slug:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tu cuenta no tiene organizacion asignada. Contacta a un administrador.",
        )
    return user.org_slug


def _encode_cursor(row: dict[str, Any]) -> str:
    crudo = f"{row['captured_at']}|{row['event_id']}"
    return base64.urlsafe_b64encode(crudo.encode()).decode()


def _decode_cursor(cursor: str | None) -> tuple[str, str] | None:
    if not cursor:
        return None
    try:
        captured_at, event_id = base64.urlsafe_b64decode(cursor).decode().split("|", 1)
    except Exception as exc:  # noqa: BLE001 - cursor manipulado o de otra version
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Cursor invalido"
        ) from exc
    return captured_at, event_id


# ---------------------------------------------------------------------------
# Fichas de animales
# ---------------------------------------------------------------------------


def _write_scope(user: AuthUser, org: str | None) -> str:
    """Organizacion sobre la que se escribe.

    Un superusuario no tiene organizacion propia, asi que para escribir tiene
    que decir cual. Adivinarla seria escribir en el rancho equivocado.
    """
    if user.is_superuser:
        if not org:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Como superusuario, indica la organizacion con ?org=<slug>",
            )
        return org
    return _scope(user)  # type: ignore[return-value]


@app.get("/v1/animals")
def get_animals(user: CurrentUser) -> dict[str, Any]:
    return {"animals": animals_mod.list_animals(_require_postgres(), org_slug=_scope(user))}


@app.get("/v1/animals/{tag_id}")
def get_animal(tag_id: str, user: CurrentUser) -> dict[str, Any]:
    animal = animals_mod.get_animal(
        _require_postgres(), tag_id=tag_id, org_slug=_scope(user)
    )
    if animal is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Animal no encontrado")
    return animal


@app.put("/v1/animals/{tag_id}")
def put_animal(
    tag_id: str,
    body: AnimalIn,
    user: CurrentUser,
    org: str | None = Query(default=None),
) -> dict[str, Any]:
    try:
        return animals_mod.upsert_animal(
            _require_postgres(),
            org_slug=_write_scope(user, org),
            tag_id=tag_id,
            alias=body.alias,
            notes=body.notes,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@app.post("/v1/animals/{tag_id}/photo")
async def post_animal_photo(
    tag_id: str,
    user: CurrentUser,
    file: Annotated[UploadFile, File()],
    org: str | None = Query(default=None),
) -> dict[str, Any]:
    dsn = _require_postgres()
    org_slug = _write_scope(user, org)

    raw = await file.read()
    try:
        content_type = animals_mod.validate_photo(raw, file.content_type)
    except animals_mod.PhotoError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc

    try:
        return animals_mod.save_photo(
            dsn, org_slug=org_slug, tag_id=tag_id, raw=raw, content_type=content_type
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@app.get("/v1/animals/{tag_id}/photo")
def get_animal_photo(tag_id: str, user: CurrentUser) -> Response:
    photo = animals_mod.load_photo(
        _require_postgres(), tag_id=tag_id, org_slug=_scope(user)
    )
    if photo is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sin foto")

    return Response(
        content=photo.bytes_,
        media_type=photo.content_type,
        headers={
            # nosniff: aunque el tipo se valida contra los bytes magicos al
            # subir, servir contenido de usuario desde nuestro origen sin esto
            # deja la puerta abierta a que el navegador lo reinterprete.
            "X-Content-Type-Options": "nosniff",
            "Cache-Control": "private, max-age=300",
        },
    )


@app.delete("/v1/animals/{tag_id}/photo")
def delete_animal_photo(
    tag_id: str, user: CurrentUser, org: str | None = Query(default=None)
) -> dict[str, Any]:
    borrada = animals_mod.delete_photo(
        _require_postgres(), tag_id=tag_id, org_slug=_write_scope(user, org)
    )
    if not borrada:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sin foto")
    return {"ok": True, "tag_id": tag_id}


# Sin autenticacion a proposito: es el camino de ingest de las estaciones, y
# todavia no existe la API key por device (ticket E0-T2). Cerrar esto antes
# de que exista dejaria a las estaciones sin poder reportar, que es
# exactamente lo que el invariante raiz prohibe.
@app.post("/v1/readings")
def post_readings(body: WeightReadingIn | ReadingsBatchIn) -> dict[str, Any]:
    if isinstance(body, WeightReadingIn):
        items = [body.model_dump()]
    else:
        items = [r.model_dump() for r in body.readings]
    accepted, duplicates = store.upsert_readings(items)
    return {
        "accepted_ids": accepted,
        "duplicate_ids": duplicates,
        "count": len(accepted),
    }


@app.get("/v1/readings")
def get_readings(
    user: CurrentUser,
    limit: int = Query(default=50, ge=1, le=200),
    cursor: str | None = Query(default=None),
    device_id: str | None = Query(default=None),
    tag_id: str | None = Query(default=None),
) -> dict[str, Any]:
    """Lecturas de la organizacion del usuario. El superusuario las ve todas."""
    readings = store.list_readings(
        limit=limit,
        org_slug=_scope(user),
        device_id=device_id,
        tag_id=tag_id,
        cursor=_decode_cursor(cursor),
    )
    # Solo hay siguiente pagina si la actual vino llena. Con menos filas que el
    # limite, ya se llego al final.
    siguiente = _encode_cursor(readings[-1]) if len(readings) == limit else None
    return {"readings": readings, "next_cursor": siguiente}


@app.post("/v1/devices/{device_id}/heartbeat")
def post_heartbeat(device_id: str, body: HeartbeatIn) -> dict[str, Any]:
    store.heartbeat(
        device_id,
        pending_count=body.pending_count,
        agent_version=body.agent_version,
        uptime_s=body.uptime_s,
    )
    return {"ok": True, "device_id": device_id}


@app.get("/v1/devices")
def get_devices(user: CurrentUser) -> dict[str, Any]:
    return {"devices": store.list_devices(org_slug=_scope(user))}


def main() -> None:
    import uvicorn

    uvicorn.run(
        "fierro_api.main:app",
        host=settings.host,
        port=settings.port,
        reload=False,
    )


if __name__ == "__main__":
    main()
