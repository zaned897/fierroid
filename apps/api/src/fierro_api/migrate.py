"""Runner de migraciones SQL para la API en Postgres.

Migraciones numeradas en SQL plano en vez de Alembic: el objetivo son tablas
Timescale con DDL crudo, y un runner de 60 lineas se audita completo en un
minuto. Si el esquema crece a decenas de tablas con relaciones, migrar a
Alembic es un ticket aparte.
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

logger = logging.getLogger(__name__)

MIGRATIONS_DIR = Path(__file__).parent / "migrations"

# Lock global: varias replicas de la API pueden arrancar en el mismo segundo.
# Sin esto, dos procesos aplican la misma migracion a la vez.
_ADVISORY_LOCK_KEY = 8_113_770


def discover() -> list[Path]:
    """Migraciones en orden lexicografico (001_, 002_, ...)."""
    return sorted(MIGRATIONS_DIR.glob("*.sql"))


def apply_migrations(dsn: str) -> list[str]:
    """Aplica las migraciones pendientes. Devuelve las versiones aplicadas."""
    import psycopg

    applied: list[str] = []
    with psycopg.connect(dsn, autocommit=True) as conn, conn.cursor() as cur:
        cur.execute("SELECT pg_advisory_lock(%s)", (_ADVISORY_LOCK_KEY,))
        try:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS schema_migrations (
                  version    TEXT PRIMARY KEY,
                  applied_at TIMESTAMPTZ NOT NULL DEFAULT now()
                )
                """
            )
            cur.execute("SELECT version FROM schema_migrations")
            done = {row[0] for row in cur.fetchall()}

            for path in discover():
                version = path.stem
                if version in done:
                    continue
                logger.info("aplicando migracion %s", version)
                # Cada migracion es atomica: si el DDL falla, no queda registrada.
                with conn.transaction():
                    cur.execute(path.read_text(encoding="utf-8"))
                    cur.execute(
                        "INSERT INTO schema_migrations (version) VALUES (%s)",
                        (version,),
                    )
                applied.append(version)
        finally:
            cur.execute("SELECT pg_advisory_unlock(%s)", (_ADVISORY_LOCK_KEY,))

    return applied


def main() -> None:
    from fierro_api.settings import Settings

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    settings = Settings.from_env()
    if not settings.dsn:
        # Falla ruidosa: sin DSN no hay nada que migrar y el operador debe saberlo.
        print(
            "FIERRO_API_DSN no esta definido. Ejemplo:\n"
            "  FIERRO_API_DSN=postgresql://fierro:fierro@localhost:5432/fierro",
            file=sys.stderr,
        )
        raise SystemExit(2)

    applied = apply_migrations(settings.dsn)
    if applied:
        print(f"migraciones aplicadas: {', '.join(applied)}")
    else:
        print("sin migraciones pendientes")


if __name__ == "__main__":
    main()
