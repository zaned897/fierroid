from __future__ import annotations

import os
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

    @property
    def is_deployed(self) -> bool:
        return self.env in DEPLOYED_ENVS

    @classmethod
    def from_env(cls) -> Settings:
        # FIERRO_API_DSN definido => Postgres. Vacio => SQLite en db_path.
        dsn = os.getenv("FIERRO_API_DSN", "").strip() or None
        raw_origins = os.getenv("FIERRO_API_CORS_ORIGINS", "*")
        origins = tuple(o.strip() for o in raw_origins.split(",") if o.strip())
        return cls(
            db_path=os.getenv("FIERRO_API_DB_PATH", "/tmp/fierro-api.db"),
            host=os.getenv("FIERRO_API_HOST", "0.0.0.0"),
            port=int(os.getenv("FIERRO_API_PORT", "8000")),
            dsn=dsn,
            env=os.getenv("FIERRO_ENV", "dev").strip().lower(),
            cors_origins=origins or ("*",),
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
