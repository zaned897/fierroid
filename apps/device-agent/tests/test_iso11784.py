import pytest
from fierro_device.drivers.iso11784 import (
    NACIONAL_MAX,
    desde_bits_64,
    desde_partes,
    desde_texto,
)

ANIMAL = 1 << 63
DATOS = 1 << 48


def _bits(pais: int, nacional: int, extra: int = ANIMAL) -> int:
    return extra | (pais << 38) | nacional


def test_partes_contrato() -> None:
    assert desde_partes(982, 123456789) == "982000123456789"


def test_partes_ceros_a_la_izquierda() -> None:
    assert desde_partes(4, 7) == "004000000000007"
    assert desde_partes(0, 0) == "000000000000000"


@pytest.mark.parametrize("pais", [900, 985, 998, 999])
def test_partes_fabricante(pais: int) -> None:
    assert desde_partes(pais, 1) == f"{pais}000000000001"


def test_partes_limite_nacional() -> None:
    assert desde_partes(484, NACIONAL_MAX) == "484274877906943"


@pytest.mark.parametrize(
    ("pais", "nacional", "mensaje"),
    [
        (1000, 1, "país"),
        (-1, 1, "país"),
        (484, NACIONAL_MAX + 1, "38 bits"),
        (484, -1, "nacional"),
        (True, 1, "int"),
        (484, 1.0, "int"),
    ],
)
def test_partes_invalidas(pais: object, nacional: object, mensaje: str) -> None:
    with pytest.raises(ValueError, match=mensaje):
        desde_partes(pais, nacional)  # type: ignore[arg-type]


def test_bits_vector_publico() -> None:
    # Chip "990000005929238" read as country 0x3DE, national 0x5A7916
    # (forum.arduino.cc/t/1361712), assembled per ISO 11784:1996 Table 1.
    assert desde_bits_64(0x8000F780005A7916) == "990000005929238"


def test_bits_ignora_reservados_y_bloque_de_datos() -> None:
    reservados = 0b10110011001101 << 49
    valor = _bits(982, 123456789, ANIMAL | DATOS | reservados)
    assert desde_bits_64(valor) == "982000123456789"


@pytest.mark.parametrize(
    ("pais", "nacional"), [(0, 0), (4, 7), (484, 1), (982, 123456789), (999, NACIONAL_MAX)]
)
def test_ida_y_vuelta_bits_partes(pais: int, nacional: int) -> None:
    tag = desde_partes(pais, nacional)
    assert desde_bits_64(_bits(pais, nacional)) == tag
    assert desde_texto(tag) == tag


@pytest.mark.parametrize(
    ("valor", "mensaje"),
    [
        (_bits(982, 1, extra=0), "animal"),
        (1 << 64, "64 bits"),
        (-1, "64 bits"),
        (_bits(1000, 1), "país"),
        (_bits(1023, 1), "país"),
    ],
)
def test_bits_invalidos(valor: int, mensaje: str) -> None:
    with pytest.raises(ValueError, match=mensaje):
        desde_bits_64(valor)


@pytest.mark.parametrize(
    "texto",
    ["982 000123456789", "982000123456789", "982-000123456789", "982000123456789\r\n"],
)
def test_texto_formas_validas(texto: str) -> None:
    assert desde_texto(texto) == "982000123456789"


@pytest.mark.parametrize(
    "texto",
    [
        "",
        "982 123456789",  # nacional corto: no se rellena
        "9820001234567890",  # un dígito de más
        "982  000123456789",
        "982_000123456789",
        "982 00012345678x",
        "proto:0A1B2C3D",
        "９８２０００１２３４５６７８９",  # dígitos no ASCII
        "484999999999999",  # nacional > 2**38
    ],
)
def test_texto_invalido(texto: str) -> None:
    with pytest.raises(ValueError):
        desde_texto(texto)


def test_texto_no_str() -> None:
    with pytest.raises(ValueError, match="str"):
        desde_texto(982000123456789)  # type: ignore[arg-type]
