# Confiabilidad del device en campo

Cómo evitar que la Raspberry Pi (y lo que la rodea) falle, se corrompa o mienta.
El corral no tiene UPS de rack ni técnico de guardia: **el device tiene que salvarse solo**.

Regla base: **diseña asumiendo que la alimentación se corta en el peor instante posible.**

---

## 1. Modelo de amenazas del edge

| Amenaza | Consecuencia si no se mitiga | Mitigación |
|---|---|---|
| Corte de energía a mitad de escritura | Corrupción de FS / SD, pérdida de la última lectura | §2, §3 |
| Escrituras constantes en microSD | Desgaste → SD muerta en meses | §3 |
| Reloj sin red ni RTC | `captured_at` inventado → datos inútiles | §4 |
| Proceso colgado (serial bloqueado, deadlock) | Estación "viva" pero sin capturar | §5 |
| Disco lleno (LTE caída semanas) | Falla de inserción = lectura perdida | §6 |
| Calor en gabinete sellado al sol | Throttling, apagados, SD degradada | §7 |
| Update remoto malo | Miles de equipos brickeados | §8 |
| Brownout / 12 V sucio del rancho | Reinicios aleatorios, undervoltage | §2 |

---

## 2. Energía y apagones

**El apagón no es un caso borde; es el caso normal en un rancho.**

1. **UPS con aviso, no solo respaldo.** El HAT de batería (LiFePO4 o supercapacitores) debe **señalar la pérdida de red por GPIO/I²C**, no solo aguantar. Sin la señal, el sistema no sabe que debe apagarse limpio.
2. **Apagado ordenado disparado por esa señal:** GPIO → servicio systemd → `flush` de SQLite → `systemctl poweroff`. Presupuesto mínimo de autonomía: **30 s** después del aviso.
3. **Protección de entrada** en la línea de 12 V del rancho: fusible, protección contra inversión de polaridad y TVS. Ver [`hardware-boundary.md`](hardware-boundary.md).
4. **Reportar undervoltage en el heartbeat.** La Pi lo expone (`vcgencmd get_throttled`); un bit de undervoltage recurrente es una falla de instalación, no un misterio.
5. **Nada de apagar por corte de breaker como operación normal.** Documentar en el runbook de instalación.

## 3. Corrupción de tarjeta y durabilidad de datos

### SQLite — durabilidad real

El outbox es la definición de "lectura capturada". Debe sobrevivir a un `SIGKILL` físico.

- `journal_mode=WAL` — correcto, ya está en [`store.py`](../../apps/device-agent/src/fierro_device/store.py).
- `synchronous=NORMAL` **no** garantiza que un commit sobreviva a un corte de energía: WAL no se sincroniza a disco en cada commit. La base no se corrompe, pero **las últimas transacciones se pueden perder** — justo lo que el invariante prohíbe.
- En la ruta crítica de captura usar **`PRAGMA synchronous=FULL`**. Es más lento, y a ritmo de pesaje (segundos entre animales) el costo es irrelevante frente a perder una lectura.
- Un `fsync` solo vale si el medio no miente: usar SD/eMMC con **protección de pérdida de energía**, no una SD de consumo con caché volátil.

### Sistema de archivos

1. **Root en solo lectura con overlayfs** (`raspi-config` → *Overlay File System*). El SO no se corrompe porque nadie le escribe.
2. **Una sola partición de datos escribible**, montada aparte, solo para el outbox y el estado del agente.
3. Montar con `noatime`.
4. **Logs fuera de la SD:** `journald` en `Storage=volatile` (+ `log2ram` si se quiere retención corta). Los logs persistentes son la causa #1 de desgaste.
5. **Medio de almacenamiento:** microSD **industrial** (pSLC/SLC) como mínimo. Para producto serio: **CM4/CM5 con eMMC** o NVMe — que además es el camino natural de la PCB propia.

## 4. Tiempo — el problema silencioso

La Raspberry Pi **no tiene RTC con batería** (la Pi 5 solo trae conector para una). Sin red al arrancar, el reloj queda en la última hora conocida. Un sistema cuyo producto es *"peso X en el momento T"* no puede tener T inventado.

1. **RTC con batería en la PCB propia** (DS3231 o equivalente). Es el fix real.
2. **`chrony`/NTP** en cuanto haya LTE, con `makestep` permitido al arranque.
3. **Marcar la confianza del reloj en el evento** (`clock_synced: true|false`) para poder corregir después en la nube.
4. **La nube estampa `received_at`** además de `captured_at`. Nunca sobrescribir el del device; guardar ambos.
5. Usar **`time.monotonic()` para intervalos** (ya se hace en `main.py`) y wall-clock solo para timestamps — un salto de NTP no debe descuadrar el debounce ni el backoff.

## 5. Proceso vivo pero inútil

1. **Watchdog de hardware.** La Pi tiene watchdog en el SoC: habilitar `RuntimeWatchdogSec` en systemd. Si el kernel se cuelga, reinicia solo.
2. **Watchdog de aplicación.** El servicio del agente usa `WatchdogSec=` + `sd_notify`. Si el loop de captura deja de latir, systemd lo reinicia — un serial bloqueado no puede quedarse colgado para siempre.
3. **Timeout en toda lectura serial.** `pyserial` sin timeout bloquea indefinidamente.
4. **systemd:** `Restart=always`, `RestartSec=5`, `StartLimitIntervalSec=0` (nunca dejar de reintentar), `MemoryMax` para no tumbar el sistema por fuga.
5. **El agente arranca solo tras reinicio** y recupera la outbox: `pending` sigue `pending`. Verificar esto en tests.

## 6. Disco lleno y retención

1. **Dimensionar semanas de operación offline**, no días.
2. **Alarma temprana**: `pending_count` y `%` de disco en el heartbeat, con umbral que dispare alerta antes de la saturación.
3. **Política explícita cuando la partición se llena.** No puede ser "la inserción falla y se pierde la lectura". Definir: alertar, degradar, y solo entonces recortar — **nunca borrar `pending` sin ACK**.
4. **Purga de `synced`** con retención configurable; los que ya llegaron a la nube sí se pueden podar.

## 7. Térmica y ambiente

1. Gabinete **IP65/IP66** sellado: sin ventilación → **disipación conducida** al chasis, no ventilador.
2. **Temperatura del SoC en el heartbeat**, con throttling reportado.
3. Considerar el rango de temperatura de la SD/eMMC y la batería del UPS: **LiFePO4 tolera mejor el calor** que Li-ion.
4. Antena LTE **externa al gabinete metálico**; un corral de tubo es una jaula de Faraday.

## 8. Actualizaciones sin brickear la flota

1. **Nunca auto-update ciego simultáneo.** Rollout por lotes (canario → 5 % → resto).
2. **A/B con rollback automático** (RAUC / Mender / SWUpdate son el estándar del sector). Si el equipo no reporta salud tras N minutos, revierte solo.
3. **El outbox sobrevive al update.** La partición de datos nunca se toca en un update de sistema.
4. **Versión reportada en cada heartbeat** (`agent_version`, SemVer) — sin eso no hay forma de saber qué corre en campo.

---

## Pruebas de caos exigidas

Todo cambio en captura, outbox o sync debe pasar estas pruebas antes de mergear:

| Prueba | Criterio de aceptación |
|---|---|
| Corte de energía durante escritura (repetido) | 0 lecturas confirmadas perdidas, DB íntegra |
| `kill -9` al agente en pleno pesaje | Reinicio limpio, `pending` intacto |
| LTE caída y restaurada | Cero duplicados tras el flush, backoff con jitter |
| Partición de datos llena | Falla ruidosa y alerta; sin borrado de `pending` |
| Reloj hacia atrás / adelante | Intervalos no se rompen; timestamps marcados |
| Reinicio del sistema | Servicio arranca solo y drena la cola |

Sin hardware: usar `FIERRO_MOCK_HW=1`. Ver [`testing.md`](testing.md).

## Relacionados

- [`engineering-rules.md`](engineering-rules.md) — pilares y estándares
- [`hardware-boundary.md`](hardware-boundary.md) — protecciones eléctricas y PCB
- [`../architecture.md`](../architecture.md) — BOM y fiabilidad a escala
