"""Raw serial capture for hardware spikes (ticket #45).

Records everything a port emits: a .bin with the raw bytes and a .txt
sidecar a human can read to work out framing (per-chunk hex with
timestamps, so gaps between chunks reveal frame boundaries).

No decoding here. The driver is written later (#46), from these captures.
"""

from __future__ import annotations

import argparse
import time
from pathlib import Path

import serial


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Captura trafico serie crudo para spikes de hardware."
    )
    parser.add_argument("puerto", help="COM5, /dev/ttyUSB0, ...")
    parser.add_argument("--baudios", type=int, default=9600)
    parser.add_argument(
        "--segundos", type=float, default=15.0, help="ventana de captura"
    )
    parser.add_argument(
        "--nota", required=True, help="que hiciste para provocar este trafico"
    )
    parser.add_argument(
        "--salida",
        type=Path,
        default=Path(__file__).resolve().parent / "rfid-prototipo",
    )
    args = parser.parse_args()

    args.salida.mkdir(parents=True, exist_ok=True)
    stamp = time.strftime("%Y%m%d-%H%M%S")
    ruta_bin = args.salida / f"captura-{stamp}.bin"
    ruta_txt = args.salida / f"captura-{stamp}.txt"

    with serial.Serial(args.puerto, args.baudios, timeout=0.2) as puerto:
        print(
            f"capturando {args.puerto}@{args.baudios} "
            f"por {args.segundos}s (Ctrl+C corta antes)"
        )
        chunks: list[tuple[float, bytes]] = []
        inicio = time.monotonic()
        try:
            while time.monotonic() - inicio < args.segundos:
                datos = puerto.read(4096)
                if datos:
                    chunks.append((time.monotonic() - inicio, datos))
        except KeyboardInterrupt:
            pass

    crudo = b"".join(datos for _, datos in chunks)
    ruta_bin.write_bytes(crudo)

    duracion = f"{chunks[-1][0]:.2f}" if chunks else "0.00"
    lineas = [
        f"nota: {args.nota}",
        f"puerto: {args.puerto}",
        f"baudios: {args.baudios}",
        f"bytes: {len(crudo)}",
        f"duracion_s: {duracion}",
        "",
    ]
    for t, datos in chunks:
        lineas.append(f"t={t:08.3f} len={len(datos):4d} {datos.hex(' ')}")
    ruta_txt.write_text("\n".join(lineas) + "\n", encoding="utf-8")

    print(f"{len(crudo)} bytes -> {ruta_bin}")
    print(f"hex legible -> {ruta_txt}")


if __name__ == "__main__":
    main()
