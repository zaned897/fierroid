"""Exporta el contrato OpenAPI a un archivo versionado.

El contrato deja de ser una consecuencia del codigo y pasa a ser algo que se
revisa en el pull request. Cambiar la superficie de la API obliga a actualizar
`docs/contracts/openapi.json` en el mismo commit, y una prueba lo verifica.

    python -m fierro_api.contract          # regenerar
    python -m fierro_api.contract --check   # fallar si esta desactualizado
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

# parents[4] es la raiz del repo: fierro_api -> src -> api -> apps -> raiz.
# El modulo esta un nivel mas profundo que las pruebas, que usan parents[3].
CONTRATO = Path(__file__).resolve().parents[4] / "docs" / "contracts" / "openapi.json"


def build_spec() -> dict[str, Any]:
    """Esquema en vivo de la app.

    Se fija una ruta de base efimera antes de importar: importar la app crea el
    store, y no queremos que generar el contrato toque la base real de nadie.
    """
    os.environ.setdefault("FIERRO_API_DB_PATH", "/tmp/fierro-contract.db")
    os.environ.pop("FIERRO_API_DSN", None)

    from fierro_api.main import app

    return app.openapi()


def dump(spec: dict[str, Any]) -> str:
    # sort_keys: sin esto cada regeneracion produce un diff distinto y el
    # contrato deja de servir para revisar cambios.
    return json.dumps(spec, indent=2, ensure_ascii=False, sort_keys=True) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Exporta o verifica el contrato OpenAPI.")
    parser.add_argument(
        "--check",
        action="store_true",
        help="No escribe: falla si el archivo esta desactualizado",
    )
    args = parser.parse_args(argv)

    nuevo = dump(build_spec())

    if args.check:
        actual = CONTRATO.read_text(encoding="utf-8") if CONTRATO.exists() else ""
        if actual != nuevo:
            print(
                "El contrato esta desactualizado. Regeneralo con:\n"
                "  python -m fierro_api.contract",
                file=sys.stderr,
            )
            return 1
        print("contrato al dia")
        return 0

    CONTRATO.parent.mkdir(parents=True, exist_ok=True)
    CONTRATO.write_text(nuevo, encoding="utf-8")
    print(f"contrato escrito en {CONTRATO.relative_to(Path.cwd())}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
