"""Ayudas comunes de base de datos."""

from __future__ import annotations

from typing import TypeVar

T = TypeVar("T")


def require_row(row: T | None, context: str) -> T:
    """Convierte un `fetchone()` opcional en uno obligatorio.

    Casi todos los `fetchone()` del proyecto vienen de un `INSERT ... RETURNING`
    o de un `SELECT` por clave primaria, donde siempre hay fila **si la
    sentencia hizo lo que creemos**. Escribir `cur.fetchone()[0]` da por hecho
    ese "si" y, cuando falla, revienta con
    `TypeError: 'NoneType' object is not subscriptable`, que no dice nada.

    Esto convierte esa suposicion en una comprobacion con mensaje util, y de
    paso hace el codigo verificable por mypy.
    """
    if row is None:
        raise RuntimeError(
            f"{context}: la consulta no devolvio ninguna fila. "
            "Un RETURNING vacio significa que la sentencia no hizo lo esperado."
        )
    return row
