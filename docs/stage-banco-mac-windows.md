# Banco RFID compartido en stage: Windows y Mac

Verificado: 2026-09-26. Referencia de código: `0618389`.
Supuesto para la segunda estación: Arduino UNO/Nano + MFRC522 + potenciómetro,
igual que el prototipo documentado. Si la placa o el lector cambian, confirmar
el modelo antes de usar este firmware.

## Acceso y estaciones

Los cuatro usuarios solicitados de Bitelemetric quedaron activos, con rol normal
y organización `los-encinos`, en **stage**. Se verificó después del commit de la
transacción. No se modificó producción ni se asignaron privilegios de administrador.
Acceso por Google con el correo autorizado; no se crearon contraseñas.

| Equipo | Device ID | Organización / rancho |
|---|---|---|
| PC existente | `rpi-los-encinos-001` | `los-encinos` / `san-jose` |
| Segunda estación, Mac | `rpi-los-encinos-002` | `los-encinos` / `san-jose` |

La segunda identidad ya existía en stage con datos sintéticos y sin lecturas
de prototipo. Se reutiliza para este banco; no usarla en otro equipo simultáneo.
Los usuarios normales ven toda su organización: incluye otras estaciones demo
y datos sintéticos existentes. No se borraron ni movieron historiales.
Los dispositivos pueden funcionar simultáneamente con IDs distintos.
El nombre `rpi-` es un identificador histórico; no exige una Raspberry Pi.

API de ambos agentes:
`https://fierro-api-stage-yj7cs5a7aq-pv.a.run.app`.

## 1. Preparar la Mac una vez

Instalar Python 3.11 o posterior desde [Python para macOS](https://www.python.org/downloads/macos/).
Para el agente no hacen falta Docker, PostgreSQL, Neon ni credenciales de nube.

En Terminal:

```bash
git --version
python3 --version
mkdir -p ~/Documents/GitHub
cd ~/Documents/GitHub
git clone https://github.com/zaned897/fierroid.git
cd fierroid
git switch stage
git pull --ff-only origin stage
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e './apps/device-agent[bench]'
python -m serial.tools.list_ports -v
```

Si `git` pide las herramientas de línea de comandos de Apple, completar esa
instalación y repetir. Si el repositorio ya existe, entrar a él y actualizar
sin volver a clonarlo ni sobrescribir cambios propios.
Las comillas en `./apps/device-agent[bench]` son necesarias con zsh.

## 2. Cargar el firmware de la segunda placa

Instalar [Arduino IDE](https://support.arduino.cc/hc/en-us/articles/360019833020-Download-and-install-Arduino-IDE).
En su gestor de bibliotecas instalar **MFRC522**. Seleccionar la placa real
(UNO o Nano), su paquete de placas y su puerto USB; seguir el
[procedimiento oficial de carga](https://support.arduino.cc/hc/en-us/articles/4733418441116-Upload-a-sketch-in-Arduino-IDE).

Preparar un sketch con nombre y carpeta coincidentes, desde la raíz del repo:

```bash
mkdir -p ~/Documents/Arduino/fierro_stage
cp hardware/test-fixtures/ard_com_test.ino ~/Documents/Arduino/fierro_stage/fierro_stage.ino
```

Abrir esa copia en Arduino IDE y cargarla. Si ya existe una copia personalizada,
conservarla antes de copiar. El firmware original queda intacto en el repo.

El firmware actual usa MFRC522 por SPI: SS=D10, RST=D9, MOSI=D11,
MISO=D12, SCK=D13, GND común y **VCC a 3.3 V**; potenciómetro en A0.
Esto corresponde a UNO/Nano clásico, no a cualquier placa.

Abrir brevemente el monitor serie a **115200 baudios**, comprobar el banner,
presentar una tarjeta y observar `W,<UID>,<ADC>`. Cerrar el monitor antes de
arrancar el agente: un puerto solo puede tener un consumidor.
Usar un cable USB de datos; uno solo de carga alimenta la placa pero no crea puerto.

## 3. Identificar el puerto de la Mac

Desde el repo y con el entorno activado:

```bash
python -m serial.tools.list_ports -v
```

Comparar con la placa desconectada y conectada. Usar el puerto `/dev/cu.*`
correspondiente, por ejemplo `/dev/cu.usbmodem1101` o `/dev/cu.usbserial-...`.
El nombre es un ejemplo: copiar el que indique tu Mac. Puede cambiar al mover
el cable o el adaptador. No asumir que será igual en las dos máquinas.

## 4. Crear la configuración de la Mac

Desde la raíz del repo, crear `apps/device-agent/.env` si no existe y pegar:

```dotenv
FIERRO_HW_BACKEND=prototipo
FIERRO_MOCK_HW=0
FIERRO_RFID_PORT=/dev/cu.REEMPLAZAR_POR_TU_PUERTO
FIERRO_DEVICE_ID=rpi-los-encinos-002
FIERRO_API_URL=https://fierro-api-stage-yj7cs5a7aq-pv.a.run.app
FIERRO_DB_PATH=${HOME}/Library/Application Support/Fierro/stage-mac-002.db
FIERRO_PESO_MODO=aleatorio
```

Editar, por ejemplo, con `nano apps/device-agent/.env`: guardar con Ctrl+O,
Enter y salir con Ctrl+X. No sobrescribir un `.env` existente sin revisarlo.
Este archivo es local e ignorado por Git. No copiar la SQLite del PC a la Mac.
La carpeta de datos se crea automáticamente.

`FIERRO_PESO_MODO=aleatorio` conserva el fallback que requiere la configuración
actual. Con este firmware las líneas `W` ya incluyen ADC y **no usan ese fallback**.
No activa un emisor periódico: eso depende de `FIERRO_MOCK_HW`, que aquí es `0`.
No poner `potenciometro`: ese modo espera una función ADC inyectada en Python y
no es la configuración de este puente serie.

## 5. Iniciar las lecturas en la Mac

Cada nueva Terminal:

```bash
cd ~/Documents/GitHub/fierroid
source .venv/bin/activate
curl -fsS https://fierro-api-stage-yj7cs5a7aq-pv.a.run.app/health
python -m dotenv -f apps/device-agent/.env run --override -- python -m fierro_device.main
```

La respuesta de salud debe incluir `"env":"stage"`.
El log inicial debe mostrar `device_id=rpi-los-encinos-002`, `mock_hw=False`,
la URL de stage y la ruta persistente de la Mac. Si alguno difiere, detener con
Ctrl+C antes de presentar tarjetas.

El agente **no carga `.env` solo**: conservar el prefijo `python -m dotenv`.
Al abrir el puerto se puede reiniciar el Arduino; esperar el arranque.
Mantener la Mac despierta y conectada mientras se realiza la prueba.

## 6. Iniciar la estación existente en Windows

La configuración local revisada usa COM6, `rpi-los-encinos-001` y stage.
Conservar su outbox `${LOCALAPPDATA}/fierro-prototipo-com6.db`.

```powershell
cd C:\Users\eduardo\Documents\GitHub\fierroid
python -m pip install -e './apps/device-agent[bench]'
python -m serial.tools.list_ports -v
python -m dotenv -f apps/device-agent/.env run --override -- python -m fierro_device.main
```

Instalar solo la primera vez y usar el mismo Python para instalar y ejecutar.
Corregir COM6 en el archivo si Windows asignó otro puerto. Cerrar el monitor
serie y cualquier otro agente que tenga el puerto abierto.
El simulador de Docker no es necesario para ninguna de las dos estaciones.

## 7. Secuencia de una lectura

1. Arrancar el agente y esperar a que el lector esté listo.
2. Dejar estable el potenciómetro; acercar una tarjeta al MFRC522.
3. Esperar el mensaje `captured event_id=... tag=proto:... weight=...`.
4. Esperar `synced N readings`: confirma el ACK de la API.
5. Retirar la tarjeta. Para repetir inmediatamente **la misma**, esperar más
   de 20 segundos desde su captura anterior y volver a acercarla.
6. Comprobar el nuevo evento en el panel de stage. El panel consulta cada
   30 segundos mientras está visible; también tiene Actualizar.
7. Al terminar usar Ctrl+C en ambos agentes. Ver `agent stopped`.

El firmware no emite lecturas mientras está inactivo: `H,<millis>` es un latido,
no un pesaje. La tarjeta sostenida no debe repetir eventos continuamente.
La estabilización del ADC tarda aproximadamente 800 ms; el agente rechaza las
muestras que el driver identifica como inestables. No forzar ni inventar un peso
si no aparece `captured`.

**El peso es de laboratorio**: se convierte el potenciómetro de 0–1023 a
30–900 kg, con pasos de 0.5 kg. `source=proto-rc522` y tags `proto:` identifican
el prototipo. El MFRC522 de 13.56 MHz no lee los aretes ganaderos LF ISO 11784.
La etiqueta visual del dashboard todavía no reconoce todas las fuentes `proto-*`;
que diga “Peso estable” no lo convierte en una medición de báscula real.

## 8. Abrir el panel local contra stage

`https://fierroid.vercel.app` usa **producción**. No comprobar allí las altas
ni las lecturas de este banco. El preview inspeccionado respondió HTML en la
ruta de configuración de API; no se verificó como acceso operativo para el equipo.

Ruta comprobada: frontend local con proxy a stage, usando el origen OAuth
`http://localhost:5173`. Para servir el frontend instalar Node.js 22 y pnpm 10
si no están disponibles; no hacen falta para ejecutar únicamente el agente.

En otra Terminal de la Mac:

```bash
cd ~/Documents/GitHub/fierroid/apps/web
npm install -g pnpm@10
pnpm install --frozen-lockfile
VITE_API_PROXY_TARGET=https://fierro-api-stage-yj7cs5a7aq-pv.a.run.app pnpm dev --host 127.0.0.1 --port 5173 --strictPort
```

En Windows, usando las dependencias existentes:

```powershell
cd C:\Users\eduardo\Documents\GitHub\fierroid\apps\web
$env:VITE_API_PROXY_TARGET='https://fierro-api-stage-yj7cs5a7aq-pv.a.run.app'
node node_modules/vite/bin/vite.js --host 127.0.0.1 --port 5173 --strictPort
```

Si 5173 está ocupado, detener solo el Vite anterior de Fierro antes de reemplazarlo.
No detener otros proyectos. `--strictPort` evita saltar silenciosamente a un puerto
que Google OAuth no tenga autorizado.

Abrir `http://localhost:5173/health`: debe indicar `stage`.
Luego abrir `http://localhost:5173/entrar` e iniciar con el correo corporativo
autorizado asociado a Google. **No usar 127.0.0.1 como URL del navegador**.
Si tenías sesión contra la API local o producción, cerrar sesión y volver a
entrar: las credenciales no se comparten entre bases de datos.
No definir `VITE_API_BASE` hacia producción: dejarlo sin definir para usar el proxy.

Los compañeros necesitan ese frontend en sus propias máquinas o un acceso web
stage con OAuth verificado; `localhost` siempre designa la máquina de cada persona.

## 9. Verificar la cola sin modificarla

En otra Terminal de la Mac:

```bash
sqlite3 -readonly "$HOME/Library/Application Support/Fierro/stage-mac-002.db" \
  'SELECT status, count(*) FROM readings GROUP BY status;'
sqlite3 -readonly "$HOME/Library/Application Support/Fierro/stage-mac-002.db" \
  'SELECT device_id,tag_id,weight_kg,source,status FROM readings ORDER BY created_at DESC LIMIT 5;'
```

`pending` significa guardado localmente y pendiente de ACK; `synced`, confirmado.
No borrar la base, no copiarla entre estaciones y no ejecutar dos agentes sobre
la misma outbox. No cambiar la URL a producción con pendientes de stage.
Si se cae la red, conservar la SQLite y reanudar contra el mismo entorno.
La configuración actual usa SQLite WAL con `synchronous=NORMAL`; no se ha
certificado resistencia a apagones. Detener ordenadamente, no cortar la energía.

## Problemas frecuentes

| Síntoma | Revisión |
|---|---|
| Puerto no aparece | Cable de datos, adaptador, placa detectada; repetir `list_ports` al conectar. |
| Puerto ocupado | Cerrar Serial Monitor/Plotter, capturador y otro agente; un único lector del puerto. |
| Lector no detectado | Revisar alimentación 3.3 V y pines del modelo de placa. |
| No llega `captured` | Tarjeta retirada y reintroducida, debounce de 20 s, potenciómetro estable, firmware `W,uid,adc`. |
| Hay `captured` pero no `synced` | Probar `/health`, revisar conexión y errores; no borrar pendientes. |
| Sin lecturas en panel | Verificar `/health` del panel = stage, cuenta/organización, ID de estación y pulsar Actualizar. |
| Google rechaza el origen | Usar `localhost:5173`; puerto y origen deben estar autorizados en OAuth. |
| Error de certificado Python | Ejecutar el instalador de certificados incluido con Python de python.org; no desactivar TLS. |

## Alcance de la comprobación

Se verificaron API stage, altas persistidas y proxy Vite→stage (HTTP 200 con
`env=stage`). No se ejecutó la nueva estación física ni se inició Google con
las cuatro cuentas. La segunda placa todavía debe construirse y probarse.
