#!/usr/bin/env python3
"""Comprueba que las herramientas instaladas son las que fija el repo.

Existe por un fallo concreto: `mypy` local era 2.3.1 y `requirements-dev.txt`
fija 1.15.0. Las dos versiones resuelven los genericos distinto, asi que el
gate local pasaba y CI fallaba con un error que en esta maquina no existia.

`install-deps.sh` instala los pins correctamente. El problema no es ponerlos,
es que nada avisaba cuando algo los pisaba despues. Un gate que mide algo
distinto de CI no es un gate: es una senal falsa, que es justo lo que las
reglas del repo prohiben.

Sin dependencias: corre con el `python` que tenga el entorno delante.
"""

from __future__ import annotations

import re
import sys
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

PINS = Path(__file__).resolve().parent.parent / "requirements-dev.txt"
LINEA = re.compile(r"^([A-Za-z0-9._-]+)==([^\s#]+)")


def main() -> int:
    problemas: list[str] = []

    for linea in PINS.read_text(encoding="utf-8").splitlines():
        hallado = LINEA.match(linea.strip())
        if not hallado:
            continue
        paquete, fijado = hallado.groups()
        try:
            instalado = version(paquete)
        except PackageNotFoundError:
            problemas.append(f"  {paquete}: no esta instalado (el repo fija {fijado})")
            continue
        if instalado != fijado:
            problemas.append(f"  {paquete}: instalado {instalado}, el repo fija {fijado}")

    if not problemas:
        return 0

    print("El entorno no coincide con requirements-dev.txt:", file=sys.stderr)
    print("\n".join(problemas), file=sys.stderr)
    print(
        "\nCon estas versiones el gate local mide algo distinto que CI.\n"
        "Se arregla con:\n\n"
        f"    pip install -r {PINS.name}\n",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
