# Spike #45 — qué manda realmente el lector RFID del prototipo

> **Timebox: 4 horas.** Si al terminar no hay captura, se escala en vez de seguir probando.
> Modelo identificado: **MFRC522** (13.56 MHz, ISO 14443A) sobre Arduino UNO/Nano — firmware en
> [`../ard_com_test.ino`](../ard_com_test.ino).

## Dónde queda la frontera en el banco

```
[lector RFID] --UART--> [Arduino] --USB-CDC--> [COM del PC] --> captura_serial.py / driver (#46)
```

El Arduino es hardware: sólo lee el lector y el potenciómetro y **re-emite tramas crudas**.
No lleva JSON, ni timestamp, ni `event_id`, ni habla con la nube — eso lo añade el agente
(`fierro-device`) aguas abajo, y es lo que garantiza la outbox SQLite y la idempotencia.
Si el lector es USB directo, se captura el lector mismo y el Arduino no participa en esta vía.

## Cómo capturar

```bash
# puerto Windows (ajustar COM y baudios)
python hardware/test-fixtures/captura_serial.py COM5 --baudios 9600 \
    --nota "lectura limpia de un tag apoyado en la antena"
```

- Baudios a probar en orden: **9600, 115200, 19200, 38400, 57600** (USB-CDC suele ignorar el valor)
- Formato fijo: 8N1; si hay basura consistente, probar 7E1
- Cada corrida produce `captura-<fecha>.bin` (bytes crudos) y `.txt` (hex legible con marcas de tiempo)

## Capturas requeridas (mínimo 4)

| Archivo | Cómo provocarla | Nota de una línea |
|---|---|---|
| captura limpia | un solo tag apoyado en la antena, sin mover | pendiente |
| dos tags seguidos | apoyar tag A, retirar, apoyar tag B | pendiente |
| trama partida | no ocurre a nivel PC: líneas ASCII de ~20 bytes a 115200 llegan casi siempre completas (capturas de chunks lo demuestran); el driver igual lleva buffer de línea | contestado por análisis |
| ruido sin tag | antena encendida, sin ningún tag cerca | `captura-20260906-223853` — banner + latidos H, sin datos |

## Preguntas que el spike contesta por escrito

1. ¿Qué emite exactamente al leer un tag? — pegar los bytes
2. ¿Emite algo cuando **no** hay tag? ¿Repite mientras el tag sigue en la antena?
3. ¿El identificador es un UID del chip (4–7 bytes) o un código ISO 11784 de 15 dígitos?
4. ¿Hay checksum, terminador de línea, prefijo?

La 3 es la que más importa: define si los datos del prototipo conviven con los de ganado real
o van marcados aparte (los tags del prototipo van prefijados `proto:` si no emiten ISO 11784).

## Respuestas

- **Modelo / frecuencia / interfaz**: MFRC522 (v. silicona 0x92), 13.56 MHz, ISO 14443A — puente Arduino
  UNO/Nano por USB-CDC, **115200 8N1**. Firmware: `ard_com_test.ino` (pesaje por evento: el tag abre
  sesión, el peso se emite UNA vez al estabilizar o por timeout).
- **1. Qué emite al leer un tag**: línea `W,<uid-hex>,<adc 0-1023>` — evento completo, tag y peso ya
  emparejados en el micro. Diagnóstico en líneas `# ...` (ignorables). Bytes reales en las capturas.
- **2. Sin tag**: no emite datos; sólo `H,<millis>` cada 10 s (latido de enlace, no es dato).
  La misma tarjeta quieta no repite `W`; retirar > 400 ms reabre sesión.
- **3. UID vs ISO 11784**: UID MIFARE de 4 bytes (ISO 14443A), **no** ISO 11784. Los tags del
  prototipo van prefijados `proto:` en el lado Python y marcados aparte de los datos reales.
- **4. Checksum / terminador / prefijo**: sin checksum en la línea (el CRC 14443A es interno del
  RC522; el ADC sale promediado de la ventana estable). Terminador **CRLF**. Prefijos de línea:
  `W` dato · `H` latido · `#` comentario.

## Hallazgos para el driver (#46)

- **Abrir el puerto resetea el Arduino** (DTR): llegan banner + `cfg ...` + versión antes de datos —
  el driver debe consumir el banner y no tratarlo como evento. La captura de ruido lo demuestra.
- Los chunks serie no siempre traen líneas completas → buffer de línea obligatorio.
- Conversiones del lado PC (regla del límite): mapear ADC 0-1023 → 30-900 kg, cuantizar a 0.5 kg,
  prefijo `proto:` en el tag, `source` del backend (`proto-rc522`). El micro no sabe nada de esto.
