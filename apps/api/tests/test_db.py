"""El ayudante que convierte un fetchone() opcional en obligatorio."""

from __future__ import annotations

import pytest
from fierro_api.db import require_row


def test_devuelve_la_fila_tal_cual():
    fila = {"id": 7, "slug": "los-encinos"}
    assert require_row(fila, "buscar organizacion") is fila


def test_una_tupla_tambien_pasa_intacta():
    assert require_row((7, "los-encinos"), "crear rancho") == (7, "los-encinos")


def test_sin_fila_falla_con_contexto():
    """El punto: que el error diga que operacion fallo, no 'NoneType'."""
    with pytest.raises(RuntimeError, match="emitir API key"):
        require_row(None, "emitir API key")


def test_el_mensaje_explica_que_significa():
    with pytest.raises(RuntimeError, match="RETURNING vacio"):
        require_row(None, "crear usuario")


def test_una_fila_vacia_no_es_lo_mismo_que_ninguna():
    """Una tupla vacia es una fila; None es que no hubo ninguna."""
    assert require_row((), "consulta rara") == ()
    assert require_row({}, "consulta rara") == {}
