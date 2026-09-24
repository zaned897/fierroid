# Device agent (Raspberry Pi)

Captures RFID + stable weight, writes to SQLite outbox first, then syncs to the API.

```bash
FIERRO_MOCK_HW=1 FIERRO_API_URL=http://127.0.0.1:8000 fierro-device
```

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
python -m dotenv -f apps/device-agent/.env run --override -- python -m fierro_device.main
```

El agente no carga `.env` por sí solo. El comando anterior carga ese archivo y
da prioridad a sus valores sobre los heredados de PowerShell, solo en el proceso
hijo. No cambia las variables de la terminal. `python -m fierro_device.main`
sin el prefijo sigue usando únicamente el entorno del proceso.

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
