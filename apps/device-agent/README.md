# Device agent (Raspberry Pi)

Captures RFID + stable weight, writes to SQLite outbox first, then syncs to the API.

Para usar las estaciones físicas compartidas en stage, seguir la
[guía de configuración y lecturas en Mac y Windows](../../docs/stage-banco-mac-windows.md).

```bash
FIERRO_MOCK_HW=1 FIERRO_API_URL=http://127.0.0.1:8000 fierro-device
fierro-device doctor   # revisa config, puerto, outbox y API sin capturar
```

## Configuración

El agente carga su configuración solo, del primer archivo que exista:

1. `FIERRO_ENV_FILE`, si está definida (si apunta a un archivo inexistente, falla).
2. Archivo del sistema: `~/.config/fierro/device.env` (Linux/RPi),
   `~/Library/Application Support/Fierro/device.env` (Mac),
   `%APPDATA%\Fierro\device.env` (Windows).
3. `apps/device-agent/.env`, para bancos con el repo clonado.

Las variables ya definidas en el proceso tienen prioridad sobre el archivo.
Con hardware real (`FIERRO_MOCK_HW` distinto de `1`, el valor por defecto)
el agente se niega a arrancar sin `FIERRO_DEVICE_ID` y `FIERRO_API_URL`.
Simular exige `FIERRO_MOCK_HW=1` explícito y el log lo advierte.

Si no se define `FIERRO_DB_PATH`, la outbox va a una ruta persistente:
`~/.local/share/fierro/outbox.db`, `~/Library/Application Support/Fierro/outbox.db`
o `%LOCALAPPDATA%\Fierro\outbox.db`. Nunca a `/tmp`.

## Prototipo Windows (COM6) con archivo de configuración

Desde la raíz del repositorio, instalar una vez en el entorno Python usado:

```powershell
python -m pip install -e './apps/device-agent[bench]'
Copy-Item apps/device-agent/.env.example apps/device-agent/.env
```

Copiar solo si aún no existe el archivo local; no sobrescribir configuraciones
personalizadas. `.env` queda ignorado por Git; `.env.example` se versiona.
Este archivo es independiente del `.env` general de la raíz (API/web/Compose).

Cerrar el monitor serial de Arduino y arrancar desde la raíz del repositorio:

```powershell
python -m fierro_device.main
```

El agente carga `apps/device-agent/.env` por sí solo (ver Configuración).
Una variable `FIERRO_*` que ya exista en PowerShell gana sobre el archivo;
si dudas, `fierro-device doctor` muestra los valores efectivos.
El comando anterior con `python -m dotenv ... run --override` sigue funcionando.

- El ejemplo usa hardware real del prototipo en COM6 y envía lecturas a stage.
- Cambiar puerto y estación cuando corresponda; la estación debe estar registrada.
- `${LOCALAPPDATA}` se expande mediante python-dotenv. No es sintaxis PowerShell.
  En Linux/RPi, sustituir esta ruta por una ubicación persistente apropiada.
- Se conserva `fierro-prototipo-com6.db`, sin cambiar ni borrar la outbox anterior.
- `FIERRO_PESO_MODO=aleatorio` explicita el fallback predeterminado del backend y
  reemplaza valores heredados. Las líneas `W,<uid>,<adc>` del micro ya llevan el
  peso: pasan por el driver sin utilizar ese fallback. No dejar el valor vacío.
- Esperar más de 20 segundos entre capturas de la misma tarjeta.
- `captured` confirma persistencia local; `synced` confirma ACK de la API.
- Detener con Ctrl+C. Abrir COM6 puede reiniciar el micro: esperar unos segundos.

## Rechazos de lecturas en el sync

Solo `accepted_ids` / `duplicate_ids` del servidor para los `event_id` enviados
permiten marcar una lectura `synced`. Ante validación HTTP 400/422, un `event_id`
explícito (en la raíz del JSON o en `detail`) identifica la lectura que pasa a
`quarantined`. Se conserva íntegro su payload y se guarda el código HTTP y el
cuerpo de respuesta en `quarantine_reason`; también se registra un error en el log.
Un ID ajeno al envío no cambia ninguna lectura.

Si el rechazo no identifica la lectura, no se pone el lote en cuarentena: los
siguientes ciclos envían una lectura por vez. Solo su rechazo individual permite
ponerla en cuarentena. Se vuelve a lotes de 50 al aislar una lectura rechazada o
vaciar la cola. Cada ciclo hace una sola petición, dejando avanzar captura,
heartbeat y watchdog. Un reinicio puede repetir el aislamiento de forma segura.

5xx, timeout, red y otros 4xx (incluidos autenticación y límites) dejan las
lecturas `pending` y mantienen el backoff con jitter. La cuarentena queda fuera
del envío automático y requiere revisión; nunca se borra ni se convierte en
`synced`. La migración añade únicamente la columna nullable `quarantine_reason`
si falta, sin reconstruir tablas ni modificar los datos previos.
