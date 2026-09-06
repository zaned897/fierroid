# Spike #45 — qué manda realmente el lector RFID del prototipo

> **Timebox: 4 horas.** Si al terminar no hay captura, se escala en vez de seguir probando.
> Este directorio queda renombrado a `rfid-<modelo>/` en cuanto el spike identifique el modelo exacto.

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
| trama partida | retirar el tag a mitad de emisión (o cortar la captura a la mitad) | pendiente |
| ruido sin tag | antena encendida, sin ningún tag cerca | pendiente |

## Preguntas que el spike contesta por escrito

1. ¿Qué emite exactamente al leer un tag? — pegar los bytes
2. ¿Emite algo cuando **no** hay tag? ¿Repite mientras el tag sigue en la antena?
3. ¿El identificador es un UID del chip (4–7 bytes) o un código ISO 11784 de 15 dígitos?
4. ¿Hay checksum, terminador de línea, prefijo?

La 3 es la que más importa: define si los datos del prototipo conviven con los de ganado real
o van marcados aparte (los tags del prototipo van prefijados `proto:` si no emiten ISO 11784).

## Respuestas

(modelo / frecuencia / interfaz / baudios / trama — se llenan con las capturas)
