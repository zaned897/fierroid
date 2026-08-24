from __future__ import annotations

import logging
import signal
import time

from fierro_device import __version__
from fierro_device.hardware import build_hardware
from fierro_device.models import WeightReading
from fierro_device.settings import Settings
from fierro_device.store import OutboxStore
from fierro_device.sync import CloudSync

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger("fierro_device")


class Agent:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
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
        self._last_sync = 0.0
        self._last_heartbeat = 0.0
        self._last_tag: str | None = None
        self._last_tag_at = 0.0

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
        pending = self.store.pending(limit=50)
        if not pending:
            return 0
        try:
            accepted = self.sync.push_readings(pending)
            self.store.mark_synced(accepted)
            logger.info("synced %d readings", len(accepted))
            return len(accepted)
        except Exception:
            logger.exception("sync failed; readings remain pending")
            return 0

    def maybe_heartbeat(self) -> None:
        now = time.monotonic()
        if now - self._last_heartbeat < 30:
            return
        try:
            self.sync.heartbeat(
                pending_count=self.store.pending_count(),
                agent_version=__version__,
                uptime_s=now - self._started,
            )
            self._last_heartbeat = now
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
        while self._running:
            try:
                self.capture_once()
            except NotImplementedError:
                logger.error("hardware not implemented; exiting")
                break
            except Exception:
                logger.exception("capture loop error")
            now = time.monotonic()
            if now - self._last_sync >= self.settings.sync_interval_s:
                self.flush_outbox()
                self._last_sync = now
            self.maybe_heartbeat()
            time.sleep(self.settings.poll_interval_s)
        self.sync.close()
        self.store.close()
        logger.info("agent stopped")


def main() -> None:
    settings = Settings.from_env()
    Agent(settings).run()


if __name__ == "__main__":
    main()
