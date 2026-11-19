"""ISO 11784 animal tag codes normalized to the 15-digit `tag_id` (ticket #180).

The data contract (docs/data-contract.md) carries `tag_id` as 15 decimal
digits: 3 of country or manufacturer code plus 12 of national identification
code, zero padded, e.g. "982000123456789". Whatever shape the fixed FDX-B
reader emits (decimal ASCII, the 64-bit code, a binary frame), it ends here.

Pure functions, no I/O and no driver wiring yet. Anything that does not fit
the standard raises ValueError: a tag is never "approximated" or repaired,
because a weighing booked to the wrong animal is worse than a loud failure.
"""

from __future__ import annotations

import re

PAIS_MAX = 999
NACIONAL_BITS = 38
NACIONAL_MAX = (1 << NACIONAL_BITS) - 1  # 274 877 906 943, fits in 12 digits
PAIS_BITS = 10

_TEXTO = re.compile(r"([0-9]{3})[ -]?([0-9]{12})")


def _entero(nombre: str, valor: object) -> int:
    # bool is an int subclass; True as a country code is a bug upstream.
    if isinstance(valor, bool) or not isinstance(valor, int):
        raise ValueError(f"{nombre} debe ser int, llegó {type(valor).__name__}")
    return valor


def desde_partes(pais: int, nacional: int) -> str:
    """Country/manufacturer code and national ID to the 15-digit tag_id.

    `pais` is the 10-bit field restricted to 0-999 (ISO 3166 numeric, or
    900-998 for manufacturers, 999 for test transponders). `nacional` is the
    38-bit field, so it must be below 2**38.
    """
    pais = _entero("pais", pais)
    nacional = _entero("nacional", nacional)
    if not 0 <= pais <= PAIS_MAX:
        raise ValueError(f"código de país fuera de rango 0-{PAIS_MAX}: {pais}")
    if not 0 <= nacional <= NACIONAL_MAX:
        raise ValueError(
            f"número nacional fuera de rango 0-{NACIONAL_MAX} (38 bits): {nacional}"
        )
    return f"{pais:03d}{nacional:012d}"


def desde_bits_64(valor: int) -> str:
    """Decode the 64-bit ISO 11784 code into the 15-digit tag_id.

    Layout per ISO 11784:1996, Table 1 ("Bit number 1 in the code is the most
    significant bit (MSB)", bit 64 the LSB; fields in natural binary, high
    order bit leftmost). Mapped onto a Python int, bit n of the norm is
    `1 << (64 - n)`:

        bit 1      (int bit 63)      animal (1) / non-animal (0) flag
        bits 2-15  (int bits 62-49)  reserved
        bit 16     (int bit 48)      data block follows (1) / none (0)
        bits 17-26 (int bits 47-38)  country code, ISO 3166 numeric-3
                                     (900-998: manufacturers)
        bits 27-64 (int bits 37-0)   national identification code

    The value is the code in that MSB-first order. FDX-B sends it LSB first
    on the air (ISO 11785); reversing the bit order is the reader parser's
    job, not this function's.

    Raises ValueError for values outside 64 bits, a non-animal flag, or a
    country field above 999 (10 bits hold up to 1023, the norm does not).
    The reserved and data block bits are not interpreted and do not change
    the result.
    """
    valor = _entero("valor", valor)
    if not 0 <= valor < 1 << 64:
        raise ValueError(f"el código ISO 11784 es de 64 bits sin signo: {valor:#x}")
    if not valor >> 63:
        raise ValueError(f"bandera de animal en 0 (transpondedor no animal): {valor:#018x}")
    pais = (valor >> NACIONAL_BITS) & ((1 << PAIS_BITS) - 1)
    nacional = valor & NACIONAL_MAX
    return desde_partes(pais, nacional)


def desde_texto(texto: str) -> str:
    """Decimal ASCII forms to the 15-digit tag_id.

    Accepts "982 000123456789", "982000123456789" and "982-000123456789":
    three digits of country, at most one space or hyphen, twelve digits of
    national ID. Only surrounding whitespace (a reader's CR/LF) is dropped;
    anything else, including a short national part, is rejected rather than
    padded or trimmed.
    """
    if not isinstance(texto, str):
        raise ValueError(f"texto debe ser str, llegó {type(texto).__name__}")
    m = _TEXTO.fullmatch(texto.strip())
    if m is None:
        raise ValueError(f"arete ISO 11784 ilegible, se esperan 3+12 dígitos: {texto!r}")
    return desde_partes(int(m.group(1)), int(m.group(2)))
