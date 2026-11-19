import pytest
from fierro_device.drivers.iso11784 import (
    NACIONAL_MAX,
    desde_bits_64,
    desde_partes,
    desde_texto,
)


def test_partes_contrato() -> None:
    assert desde_partes(982, 123456789) == "982000123456789"


def test_partes_ceros_a_la_izquierda() -> None:
    assert desde_partes(4, 7) == "004000000000007"
    assert desde_partes(0, 0) == "000000000000000"


@pytest.mark.parametrize("pais", [900, 985, 998])
def test_partes_fabricante(pais: int) -> None:
    assert desde_partes(pais, 1) == f"{pais}000000000001"


def test_partes_transpondedor_de_prueba() -> None:
    assert desde_partes(999, 1008) == "999000000001008"


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


# Vectores de 64 bits escritos a mano desde ISO 11784:1996 Tabla 1 (bit 1 es
# el MSB), sin pasar por ningún helper de las pruebas.
@pytest.mark.parametrize(
    ("valor", "tag"),
    [
        # Chip "990000005929238": país 0x3DE, nacional 0x5A7916 según
        # forum.arduino.cc/t/1361712; bandera de animal en 1.
        (0x8000_F780_005A_7916, "990000005929238"),
        # Frontera país/nacional: bit 26 de la norma (int 38) es país = 1,
        # bit 27 (int 37) es el bit alto del nacional = 2**37.
        (0x8000_0040_0000_0000, "001000000000000"),
        (0x8000_0020_0000_0000, "000137438953472"),
        # Bits 17 y 64: país 512, nacional 1.
        (0x8000_8000_0000_0001, "512000000000001"),
        # Nacional con los 38 bits en 1.
        (0x8000_003F_FFFF_FFFF, "000274877906943"),
        # 484 (México) con número usando bits altos.
        (0x8000_7920_0000_0000 | 0x2A_AAAA_AAAA, "484183251937962"),
        # Reservados (bits 2-15) y bloque de datos (bit 16) no cambian el ID.
        (0xFFFF_F600_075B_CD15, "984000123456789"),
        # Bandera de animal en 0: el ID sigue siendo exacto, no se descarta.
        (0x0000_F780_005A_7916, "990000005929238"),
        (0, "000000000000000"),
    ],
)
def test_bits_vectores(valor: int, tag: str) -> None:
    assert desde_bits_64(valor) == tag


def test_bits_orden_de_bytes_del_aire() -> None:
    # FDX-B manda bit 64 primero; empaquetado LSB primero por octeto es
    # little-endian. Documentado en el docstring de desde_bits_64.
    aire = bytes.fromhex("16795a0080f70080")
    assert desde_bits_64(int.from_bytes(aire, "little")) == "990000005929238"


@pytest.mark.parametrize("tag", ["000000000000000", "004000000000007", "999274877906943"])
def test_ida_y_vuelta_texto_partes(tag: str) -> None:
    assert desde_partes(int(tag[:3]), int(tag[3:])) == desde_texto(tag) == tag


@pytest.mark.parametrize(
    ("valor", "mensaje"),
    [
        (1 << 64, "64 bits"),
        ((1 << 64) - 1, "país"),  # país 1023
        ((1 << 63) - 1, "país"),  # país 1023, bandera en 0
        (-1, "64 bits"),
        (0x8000_FA00_0000_0001, "país"),  # país 1000
        (True, "int"),
        (None, "int"),
        ("0x8000F780005A7916", "int"),
    ],
)
def test_bits_invalidos(valor: object, mensaje: str) -> None:
    with pytest.raises(ValueError, match=mensaje):
        desde_bits_64(valor)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    "texto",
    [
        "982 000123456789",
        "982000123456789",
        "982-000123456789",
        "982000123456789\r\n",
        "\t982000123456789 ",
    ],
)
def test_texto_formas_validas(texto: str) -> None:
    assert desde_texto(texto) == "982000123456789"


def test_texto_frontera_nacional() -> None:
    assert desde_texto("484274877906943") == "484274877906943"


@pytest.mark.parametrize(
    ("texto", "mensaje"),
    [
        ("", "ilegible"),
        ("982 123456789", "ilegible"),  # nacional corto: no se rellena
        ("9820001234567890", "ilegible"),  # un dígito de más
        ("982  000123456789", "ilegible"),
        ("982_000123456789", "ilegible"),
        ("982\t000123456789", "ilegible"),
        ("982 00012345678x", "ilegible"),
        ("proto:0A1B2C3D", "ilegible"),
        ("９８２０００１２３４５６７８９", "ilegible"),  # dígitos no ASCII
        ("\x02982000123456789\x03", "ilegible"),  # STX/ETX: lo quita el parser
        ("982000123456789\u00a0", "ilegible"),  # espacio no ASCII
        ("982000123456789\r\n484000000000001", "ilegible"),  # dos aretes
        ("484274877906944", "38 bits"),  # NACIONAL_MAX + 1
        ("484999999999999", "38 bits"),
    ],
)
def test_texto_invalido(texto: str, mensaje: str) -> None:
    with pytest.raises(ValueError, match=mensaje):
        desde_texto(texto)


def test_texto_no_str() -> None:
    with pytest.raises(ValueError, match="str"):
        desde_texto(982000123456789)  # type: ignore[arg-type]
