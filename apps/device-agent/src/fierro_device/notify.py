"""Aviso a systemd (`sd_notify`) por el socket `NOTIFY_SOCKET`, sin dependencias.

Sin `NOTIFY_SOCKET` (Windows, Mac, pruebas, ejecucion manual) no hace nada.
"""

from __future__ import annotations

import logging
import os
import socket

logger = logging.getLogger(__name__)

_avisado = False


def sd_notify(state: str) -> bool:
    """Manda `state` (p. ej. "READY=1") a systemd. Devuelve True si se envio."""
    global _avisado
    addr = os.getenv("NOTIFY_SOCKET")
    if not addr or not hasattr(socket, "AF_UNIX"):
        return False
    if addr.startswith("@"):
        addr = "\0" + addr[1:]  # socket abstracto de Linux
    try:
        with socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM) as sock:
            # No bloquear el bucle de captura si el socket no lee.
            sock.setblocking(False)
            sock.connect(addr)
            sock.sendall(state.encode())
        return True
    except OSError as exc:
        # Una vez: el bucle llama cada 0.5 s y no queremos llenar el journal.
        if not _avisado:
            logger.error("sd_notify fallo (%s): %s", state, exc)
            _avisado = True
        return False
