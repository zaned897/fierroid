# Servicio de la estación en la Raspberry Pi

Archivos:

- `fierro-device.service`: unidad systemd con `Type=notify`, watchdog de aplicación
  (`WatchdogSec=90`), `Restart=always` sin límite de reintentos y `MemoryMax=256M`.
- `99-fierro-serial.rules`: enlaces estables `/dev/fierro-bascula` y `/dev/fierro-lector`.

La imagen del sistema, overlayfs, RTC, router 4G y VPN van aparte (#188).

## 1. Usuario y carpetas

```bash
sudo useradd --system --create-home --groups dialout fierro
sudo mkdir -p /etc/fierro /data/fierro
sudo chown fierro:fierro /data/fierro
```

`/data` es la partición de datos; la outbox (`/data/fierro/device.db`) no vive en la raíz.
La unidad no arranca si `/data` no está montado (`RequiresMountsFor`), ni si
`/data/fierro` no existe (`ReadWritePaths` con `ProtectSystem=strict`): falla ruidosa
en vez de escribir la outbox donde se pierde.

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
# uno por adaptador
udevadm info -q property -n /dev/ttyUSB0 | grep -E 'ID_SERIAL_SHORT|ID_VENDOR_ID|ID_MODEL_ID|ID_PATH='
sudo cp deploy/rpi/99-fierro-serial.rules /etc/udev/rules.d/
sudo nano /etc/udev/rules.d/99-fierro-serial.rules       # número de serie o puerto USB físico
sudo udevadm control --reload && sudo udevadm trigger
ls -l /dev/fierro-*
```

Adaptadores CH340/PL2303 sin número de serie propio: usar la opción B de las reglas
(puerto USB físico, `ID_PATH`) y etiquetar el puerto en el gabinete.

`fierro-device doctor` muestra a qué `/dev/ttyUSB*` apunta cada puerto. A mano, con
la misma configuración que el servicio:

```bash
sudo -u fierro FIERRO_ENV_FILE=/etc/fierro/device.env FIERRO_DB_PATH=/data/fierro/device.db \
  /opt/fierro/venv/bin/fierro-device doctor
```

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
