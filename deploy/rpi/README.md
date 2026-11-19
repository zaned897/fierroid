# Servicio de la estación en la Raspberry Pi

Archivos:

- `fierro-device.service`: unidad systemd con `Type=notify`, watchdog de aplicación
  (`WatchdogSec=30`), `Restart=always` sin límite de reintentos y `MemoryMax=256M`.
- `99-fierro-serial.rules`: enlaces estables `/dev/fierro-bascula` y `/dev/fierro-lector`.

La imagen del sistema, overlayfs, RTC, router 4G y VPN van aparte (#188).

## 1. Usuario y carpetas

```bash
sudo useradd --system --create-home --groups dialout fierro
sudo mkdir -p /etc/fierro /data/fierro
sudo chown fierro:fierro /data/fierro
```

`/data` es la partición de datos; la outbox (`/data/fierro/device.db`) no vive en la raíz.

## 2. Agente

```bash
sudo python3 -m venv /opt/fierro/venv
sudo /opt/fierro/venv/bin/pip install ./apps/device-agent
```

`/etc/fierro/device.env` (dueño `root`, modo `0640`, grupo `fierro`):

```bash
FIERRO_DEVICE_ID=rancho-001
FIERRO_API_URL=https://api.ejemplo
FIERRO_SCALE_PORT=/dev/fierro-bascula
FIERRO_RFID_PORT=/dev/fierro-lector
```

## 3. Puertos estables

```bash
udevadm info -a -n /dev/ttyUSB0 | grep -m1 '{serial}'   # uno por adaptador
sudo cp deploy/rpi/99-fierro-serial.rules /etc/udev/rules.d/
sudo nano /etc/udev/rules.d/99-fierro-serial.rules       # poner los números de serie
sudo udevadm control --reload && sudo udevadm trigger
ls -l /dev/fierro-*
```

`fierro-device doctor` muestra a qué `/dev/ttyUSB*` apunta cada puerto.

## 4. Unidad

```bash
sudo cp deploy/rpi/fierro-device.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now fierro-device
journalctl -u fierro-device -f
```

Si el hardware no está configurado, el agente no sale: registra el error, deja de
capturar, sigue vaciando la outbox y lo reporta en el heartbeat (`last_error`).

## 5. Watchdog de hardware

Si el kernel se cuelga, el watchdog del SoC reinicia la Pi. En `/etc/systemd/system.conf`:

```ini
[Manager]
RuntimeWatchdogSec=15
```

y `sudo systemctl daemon-reexec`.

## Verificar la unidad

```bash
systemd-analyze verify deploy/rpi/fierro-device.service
```
