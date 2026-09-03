from __future__ import annotations

import os
import secrets
from dataclasses import dataclass, field

# dev = laboratorio y tests. stage y production son entornos desplegados y
# se validan con las mismas reglas: si algo falta, la API no arranca.
VALID_ENVS = ("dev", "stage", "production")
DEPLOYED_ENVS = ("stage", "production")


class ConfigError(RuntimeError):
    """Configuracion invalida para el entorno. Aborta el arranque."""


@dataclass(frozen=True)
class Settings:
    db_path: str
    host: str
    port: int
    dsn: str | None = None
    env: str = "dev"
    cors_origins: tuple[str, ...] = field(default=("*",))
    jwt_secret: str = ""
    jwt_ttl_minutes: int = 60

    @property
    def is_deployed(self) -> bool:
        return self.env in DEPLOYED_ENVS

    @classmethod
    def from_env(cls) -> Settings:
        # FIERRO_API_DSN definido => Postgres. Vacio => SQLite en db_path.
        dsn = os.getenv("FIERRO_API_DSN", "").strip() or None
        raw_origins = os.getenv("FIERRO_API_CORS_ORIGINS", "*")
        origins = tuple(o.strip() for o in raw_origins.split(",") if o.strip())
        # En dev, un secreto aleatorio por arranque: sin secreto por defecto
        # que alguien pueda heredar a produccion sin darse cuenta. El costo es
        # que las sesiones no sobreviven un reinicio local, que da igual.
        jwt_secret = os.getenv("FIERRO_JWT_SECRET", "").strip()
        env = os.getenv("FIERRO_ENV", "dev").strip().lower()
        if not jwt_secret and env not in DEPLOYED_ENVS:
            jwt_secret = secrets.token_urlsafe(32)

        return cls(
            db_path=os.getenv("FIERRO_API_DB_PATH", "/tmp/fierro-api.db"),
            host=os.getenv("FIERRO_API_HOST", "0.0.0.0"),
            port=int(os.getenv("FIERRO_API_PORT", "8000")),
            dsn=dsn,
            env=env,
            cors_origins=origins or ("*",),
            jwt_secret=jwt_secret,
            jwt_ttl_minutes=int(os.getenv("FIERRO_JWT_TTL_MIN", "60")),
        )

    def validate(self) -> None:
        """Falla ruidosa al arrancar en vez de degradar en silencio."""
        if self.env not in VALID_ENVS:
            raise ConfigError(
                f"FIERRO_ENV invalido: {self.env!r}. Valores validos: {', '.join(VALID_ENVS)}"
            )

        if not self.is_deployed:
            return

        if not self.dsn:
            # SQLite en el /tmp de un contenedor se borra en cada reinicio.
            # Arrancar asi en un entorno desplegado pierde pesajes en silencio,
            # que es exactamente lo que el invariante raiz prohibe.
            raise ConfigError(
                f"FIERRO_API_DSN es obligatorio en {self.env}: sin Postgres, la API "
                "guardaria en SQLite efimero y perderia lecturas al reiniciar."
            )

        if "*" in self.cors_origins:
            raise ConfigError(
                f"FIERRO_API_CORS_ORIGINS no puede ser '*' en {self.env}. "
                "Lista los origenes explicitamente, separados por coma."
            )

        if len(self.jwt_secret) < 32:
            # Un secreto corto o ausente permite falsificar tokens de cualquier
            # usuario, superusuario incluido.
            raise ConfigError(
                f"FIERRO_JWT_SECRET es obligatorio en {self.env} y necesita al menos "
                "32 caracteres. Generalo con: python -c "
                "\"import secrets; print(secrets.token_urlsafe(48))\""
            )
