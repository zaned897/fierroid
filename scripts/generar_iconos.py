#!/usr/bin/env python3
"""Genera los iconos de la PWA desde el PNG de la marca. Sin dependencias.

    python3 scripts/generar_iconos.py

Solo stdlib a proposito: agregar Pillow al proyecto por un script que se corre
cuando cambia el logotipo no compensa.

El original mide 1433x1600 con el dibujo descentrado: a 32px eso se ve como un
icono torcido y pequenito. Aqui se recorta a lo que realmente pinta, se cuadra
y se reescala.
"""
import struct
import zlib
from pathlib import Path

VERDE = (26, 46, 26)      # --bg de la marca, el mismo del icon.svg que sustituye
ORO = (196, 163, 90)      # --accent


def leer_rgba(ruta):
    b = Path(ruta).read_bytes()
    w, h, prof, tipo = struct.unpack(">IIBB", b[16:26])
    assert (prof, tipo) == (8, 6)
    i, comp = 8, bytearray()
    while i < len(b):
        largo, = struct.unpack(">I", b[i:i + 4])
        if b[i + 4:i + 8] == b"IDAT":
            comp += b[i + 8:i + 8 + largo]
        i += 12 + largo
    crudo = zlib.decompress(bytes(comp))
    bpp, ancho = 4, w * 4
    pix, previa, p = bytearray(), bytearray(ancho), 0
    for _ in range(h):
        f = crudo[p]
        p += 1
        ln = bytearray(crudo[p:p + ancho])
        p += ancho
        # Los filtros de PNG son por byte y se apoyan en el pixel de la
        # izquierda (a), el de arriba (arr) y el de la diagonal (c).
        for x in range(ancho):
            a = ln[x - bpp] if x >= bpp else 0
            arr = previa[x]
            c = previa[x - bpp] if x >= bpp else 0
            if f == 1:
                ln[x] = (ln[x] + a) & 0xFF
            elif f == 2:
                ln[x] = (ln[x] + arr) & 0xFF
            elif f == 3:
                ln[x] = (ln[x] + (a + arr) // 2) & 0xFF
            elif f == 4:
                pa, pb, pc = abs(arr - c), abs(a - c), abs(a + arr - 2 * c)
                pred = a if (pa <= pb and pa <= pc) else (arr if pb <= pc else c)
                ln[x] = (ln[x] + pred) & 0xFF
        pix += ln
        previa = ln
    return w, h, pix


def escribir_rgba(ruta, w, h, pix):
    crudo = bytearray()
    for y in range(h):
        crudo.append(0)                       # filtro 0: sin filtrar
        crudo += pix[y * w * 4:(y + 1) * w * 4]

    def trozo(etq, datos):
        return (struct.pack(">I", len(datos)) + etq + datos
                + struct.pack(">I", zlib.crc32(etq + datos) & 0xFFFFFFFF))

    Path(ruta).write_bytes(
        b"\x89PNG\r\n\x1a\n"
        + trozo(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 6, 0, 0, 0))
        + trozo(b"IDAT", zlib.compress(bytes(crudo), 9))
        + trozo(b"IEND", b"")
    )


def caja_alfa(w, h, pix):
    """La caja de lo que realmente se pinta, ignorando el relleno transparente."""
    xs, ys = [], []
    for y in range(h):
        fila = pix[y * w * 4:(y + 1) * w * 4]
        for x in range(w):
            if fila[x * 4 + 3] > 8:
                xs.append(x)
                ys.append(y)
    return min(xs), min(ys), max(xs), max(ys)


def recortar_cuadrado(w, h, pix, margen=0.08):
    x0, y0, x1, y1 = caja_alfa(w, h, pix)
    lado = max(x1 - x0 + 1, y1 - y0 + 1)
    lado = int(lado * (1 + 2 * margen))
    cx, cy = (x0 + x1) // 2, (y0 + y1) // 2
    ox, oy = cx - lado // 2, cy - lado // 2
    salida = bytearray(lado * lado * 4)
    for y in range(lado):
        sy = oy + y
        if not (0 <= sy < h):
            continue
        for x in range(lado):
            sx = ox + x
            if 0 <= sx < w:
                i, j = (sy * w + sx) * 4, (y * lado + x) * 4
                salida[j:j + 4] = pix[i:i + 4]
    return lado, salida


def reducir(lado, pix, destino):
    """Promedio por caja. Solo reduce, que es lo unico que hace falta."""
    k = lado / destino
    salida = bytearray(destino * destino * 4)
    for y in range(destino):
        y0, y1 = int(y * k), max(int((y + 1) * k), int(y * k) + 1)
        for x in range(destino):
            x0, x1 = int(x * k), max(int((x + 1) * k), int(x * k) + 1)
            sa = sr = sg = sb = n = 0
            for sy in range(y0, min(y1, lado)):
                base = sy * lado * 4
                for sx in range(x0, min(x1, lado)):
                    i = base + sx * 4
                    a = pix[i + 3]
                    # Premultiplicado: sin esto los bordes se ensucian con el
                    # color de los pixeles transparentes.
                    sr += pix[i] * a
                    sg += pix[i + 1] * a
                    sb += pix[i + 2] * a
                    sa += a
                    n += 1
            j = (y * destino + x) * 4
            if sa:
                salida[j] = min(255, sr // sa)
                salida[j + 1] = min(255, sg // sa)
                salida[j + 2] = min(255, sb // sa)
            salida[j + 3] = sa // n if n else 0
    return salida


def recolorear(lado, pix, rgb):
    salida = bytearray(pix)
    for i in range(0, len(salida), 4):
        salida[i], salida[i + 1], salida[i + 2] = rgb
    return salida


def sobre_fondo(lado, marca, rgb_fondo, escala=0.62):
    """Icono maskable: fondo a sangre y la marca dentro de la zona segura."""
    fondo = bytearray()
    for _ in range(lado * lado):
        fondo += bytes((*rgb_fondo, 255))
    dentro = int(lado * escala)
    chico = reducir(lado, marca, dentro)
    off = (lado - dentro) // 2
    for y in range(dentro):
        for x in range(dentro):
            i = (y * dentro + x) * 4
            a = chico[i + 3]
            if not a:
                continue
            j = ((y + off) * lado + (x + off)) * 4
            for c in range(3):
                fondo[j + c] = (chico[i + c] * a + fondo[j + c] * (255 - a)) // 255
    return fondo


w, h, pix = leer_rgba("resources/favicon_streight_lines.png")
lado, cuadrado = recortar_cuadrado(w, h, pix)
print(f"original {w}x{h}  ->  recortado y cuadrado {lado}x{lado}")

marca512 = reducir(lado, cuadrado, 512)
escribir_rgba("apps/web/public/icon.png", 512, 512, marca512)

maskable = sobre_fondo(512, recolorear(512, marca512, ORO), VERDE)
escribir_rgba("apps/web/public/icon-maskable.png", 512, 512, maskable)

for n in ("icon.png", "icon-maskable.png"):
    print(f"  apps/web/public/{n}  {Path('apps/web/public/' + n).stat().st_size / 1024:.0f} KB")
