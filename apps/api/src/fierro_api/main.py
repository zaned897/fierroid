from __future__ import annotations

from typing import Annotated, Any

from fastapi import Depends, FastAPI, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field

from fierro_api import __version__
from fierro_api.auth import (
    AuthError,
    AuthUser,
    authenticate,
    create_access_token,
    decode_access_token,
    get_user,
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


@app.post("/v1/auth/login")
def login(body: LoginIn) -> dict[str, Any]:
    dsn = _require_postgres()
    try:
        # argon2 tarda ~50-100 ms a proposito: es el freno natural a la fuerza
        # bruta mientras no haya limitacion de intentos.
        user = authenticate(dsn, body.email, body.password)
    except AuthError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)
        ) from exc

    token, expires_in = create_access_token(
        user, secret=settings.jwt_secret, ttl_minutes=settings.jwt_ttl_minutes
    )
    return {
        "access_token": token,
        "token_type": "bearer",
        "expires_in": expires_in,
        "user": user.to_public(),
    }


def current_user(creds: BearerCreds) -> AuthUser:
    if creds is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Falta el encabezado Authorization",
        )
    dsn = _require_postgres()
    try:
        claims = decode_access_token(creds.credentials, secret=settings.jwt_secret)
    except AuthError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)
        ) from exc

    # Se relee el usuario en vez de confiar solo en los claims. Cuesta un
    # lookup por PK y a cambio desactivar una cuenta la corta de inmediato,
    # que es la unica revocacion que existe con JWT en localStorage.
    user = get_user(dsn, int(claims["sub"]))
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="El usuario ya no existe o esta desactivado",
        )
    return user


CurrentUser = Annotated[AuthUser, Depends(current_user)]


@app.get("/v1/auth/me")
def me(user: CurrentUser) -> dict[str, Any]:
    return user.to_public()


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
def get_readings(limit: int = Query(default=50, ge=1, le=500)) -> dict[str, Any]:
    return {"readings": store.list_readings(limit=limit)}


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
def get_devices() -> dict[str, Any]:
    return {"devices": store.list_devices()}


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
