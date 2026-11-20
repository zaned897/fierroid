from __future__ import annotations

import argparse
import logging
import random
import signal
import sys
import time
from collections.abc import Callable

from fierro_device import __version__
from fierro_device.backoff import Backoff, guardar_estado
from fierro_device.config import ConfigError, load_config
from fierro_device.hardware import build_hardware
from fierro_device.models import WeightReading
from fierro_device.notify import sd_notify
from fierro_device.settings import Settings
from fierro_device.store import OutboxStore
from fierro_device.sync import CloudSync, ReadingRejected

# Rechazos consecutivos que se aceptan como lecturas venenosas antes de suponer
# que el problema es del servidor y dejar de poner lecturas en cuarentena.
CUARENTENAS_SEGUIDAS_MAX = 5

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger("fierro_device")


class Agent:
    def __init__(
        self,
        settings: Settings,
        reloj: Callable[[], float] = time.monotonic,
        aleatorio: Callable[[], float] = random.random,
    ) -> None:
        self.settings = settings
        self._reloj = reloj
        self.store = OutboxStore(settings.db_path)
        self.hw = build_hardware(
            mock=settings.mock_hw,
            scale_port=settings.scale_port,
            rfid_port=settings.rfid_port,
            mock_interval_s=settings.mock_interval_s,
        )
        self.sync = CloudSync(settings.api_url, settings.device_id)
        self._running = True
        self._started = time.monotonic()
        self._next_sync = 0.0
        self._isolate_readings = False
        self._cuarentenas_seguidas = 0
        self.backoff = Backoff(settings.sync_interval_s, settings.sync_max_s, aleatorio)
        self._last_heartbeat = float("-inf")  # primer heartbeat al arrancar
        self._last_tag: str | None = None
        self._last_tag_at = 0.0
        # Error de hardware sin configurar: se registra una vez y se deja de capturar.
        self._hw_error: str | None = None

    def stop(self, *_args: object) -> None:
        logger.info("shutdown requested")
        self._running = False

    def _should_accept_tag(self, tag_id: str) -> bool:
        now = time.monotonic()
        # Debounce same tag within 20s to avoid duplicate alley reads
        if tag_id == self._last_tag and (now - self._last_tag_at) < 20:
            return False
        self._last_tag = tag_id
        self._last_tag_at = now
        return True

    def capture_once(self) -> WeightReading | None:
        sample = self.hw.read()
        if not sample.tag_id or sample.weight_kg is None or not sample.stable:
            return None
        if not self._should_accept_tag(sample.tag_id):
            return None
        reading = WeightReading.create(
            device_id=self.settings.device_id,
            tag_id=sample.tag_id,
            weight_kg=sample.weight_kg,
            source=sample.source,
            stable=sample.stable,
        )
        inserted = self.store.save_reading(reading)
        if inserted:
            logger.info(
                "captured event_id=%s tag=%s weight=%.1f",
                reading.event_id,
                reading.tag_id,
                reading.weight_kg,
            )
            return reading
        logger.warning("duplicate event_id locally: %s", reading.event_id)
        return None

    def flush_outbox(self) -> int:
        pending = self.store.pending(limit=1 if self._isolate_readings else 50)
        if not pending:
            self._isolate_readings = False
            return 0
        antes = self.backoff.intervalo_s
        try:
            try:
                accepted = self.sync.push_readings(pending)
            except ReadingRejected as exc:
                if exc.event_id is None:
                    # Una peticion por ciclo: no bloquear captura/heartbeat con 50 timeouts.
                    self._isolate_readings = True
                    logger.warning("rechazo sin event_id; se aislaran las lecturas: %s", exc)
                    self.backoff.fallo()
                elif self._cuarentenas_seguidas >= CUARENTENAS_SEGUIDAS_MAX:
                    # Tantos rechazos sin un solo ACK huelen a falla del servidor
                    # (esquema nuevo, proxy): mejor atascar ruidoso que vaciar la cola.
                    logger.error(
                        "%d lecturas seguidas en cuarentena sin ningun ACK; event_id=%s "
                        "queda pending hasta que el servidor acepte alguna: %s",
                        self._cuarentenas_seguidas,
                        exc.event_id,
                        exc.reason,
                    )
                    self.backoff.fallo()
                else:
                    self.store.mark_quarantined(exc.event_id, exc.reason)
                    self._cuarentenas_seguidas += 1
                    logger.error("quarantined event_id=%s: %s", exc.event_id, exc.reason)
                    self._isolate_readings = False
                    self.backoff.exito()  # progreso local; no es un ACK ni cuenta como synced
                return 0
            self.store.mark_synced(accepted)
            logger.info("synced %d readings", len(accepted))
            if accepted:
                self._cuarentenas_seguidas = 0
                self.backoff.exito()
            else:
                # 200 sin confirmar nada: la API esta degradada, no reintentar a 2 s.
                logger.warning("sync sin ACK de %d lecturas; quedan pending", len(pending))
                self.backoff.fallo()
            return len(accepted)
        except Exception:
            logger.exception("sync failed; readings remain pending")
            self.backoff.fallo()
            return 0
        finally:
            if self.backoff.intervalo_s != antes:
                self._guardar_estado_sync()

    def _guardar_estado_sync(self) -> None:
        try:
            guardar_estado(self.settings.db_path, {"intervalo_s": self.backoff.intervalo_s})
        except OSError:
            logger.exception("no se pudo guardar el estado del sync")

    def maybe_sync(self) -> None:
        now = self._reloj()
        if now < self._next_sync:
            return
        self.flush_outbox()
        self._next_sync = self._reloj() + self.backoff.espera()

    def maybe_heartbeat(self) -> None:
        now = time.monotonic()
        if now - self._last_heartbeat < 30:
            return
        # Por intento, no por exito: sin red, reintentar en cada vuelta sumaria un
        # timeout por vuelta y systemd mataria al agente por watchdog.
        self._last_heartbeat = now
        try:
            self.sync.heartbeat(
                pending_count=self.store.pending_count(),
                agent_version=__version__,
                uptime_s=now - self._started,
                last_error=self._hw_error,
            )
        except Exception:
            logger.exception("heartbeat failed")

    def run(self) -> None:
        signal.signal(signal.SIGINT, self.stop)
        signal.signal(signal.SIGTERM, self.stop)
        logger.info(
            "agent start device_id=%s mock_hw=%s api=%s db=%s",
            self.settings.device_id,
            self.settings.mock_hw,
            self.settings.api_url,
            self.settings.db_path,
        )
        # Al arrancar el intervalo vuelve al minimo: que doctor no vea el de la corrida anterior.
        self._guardar_estado_sync()
        sd_notify("READY=1")
        while self._running:
            if self._hw_error is None:
                try:
                    self.capture_once()
                except NotImplementedError as exc:
                    # Salir con Restart=always seria un bucle de reinicios: seguimos
                    # vaciando la outbox y avisando por heartbeat, sin capturar.
                    self._hw_error = str(exc) or type(exc).__name__
                    logger.error("hardware not configured; capture disabled: %s", exc)
                except Exception:
                    logger.exception("capture loop error")
            self.maybe_sync()
            self.maybe_heartbeat()
            # Solo si la vuelta termino: una lectura colgada deja de latir y systemd reinicia.
            sd_notify("WATCHDOG=1")
            time.sleep(self.settings.poll_interval_s)
        sd_notify("STOPPING=1")
        self.sync.close()
        self.store.close()
        logger.info("agent stopped")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="fierro-device")
    parser.add_argument(
        "comando",
        nargs="?",
        default="run",
        choices=("run", "doctor"),
        help="run (por defecto) captura y sincroniza; doctor revisa la estacion",
    )
    args = parser.parse_args(argv)
    try:
        config_path = load_config()
    except ConfigError as exc:
        logger.error("%s", exc)
        return 2
    settings = Settings.from_env()
    if args.comando == "doctor":
        from fierro_device.doctor import run_doctor

        return run_doctor(settings, config_path)
    logger.info("config file=%s", config_path or "(ninguno, solo entorno)")
    problems = settings.problems()
    if problems:
        for problem in problems:
            logger.error("config: %s", problem)
        return 2
    if settings.mock_hw:
        logger.warning("MODO SIMULADO: FIERRO_MOCK_HW=1, las lecturas no son reales")
    Agent(settings).run()
    return 0


if __name__ == "__main__":
    sys.exit(main())
