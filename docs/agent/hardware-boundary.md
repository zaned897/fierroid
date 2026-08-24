# Frontera hardware / software

Fierro es un producto físico. La regla que mantiene ambos mundos avanzando en paralelo:

> **El software no sabe de baudios. El hardware no sabe de negocio.**
> Todo lo que cruza pasa por un contrato explícito.

---

## 1. El contrato es el HAL

La frontera ya existe en el repo: el `Protocol` **`HardwareBackend`** en [`hardware.py`](../../apps/device-agent/src/fierro_device/hardware.py).

```
[Indicador RS232] ─┐
                   ├→ driver ─→ HardwareBackend.read() → HardwareSample ─→ lógica de negocio
[Lector RFID]     ─┘           (aquí termina el hardware)
```

**Reglas:**

1. **Nada de detalles físicos arriba del HAL.** Baudios, framing, checksums, pines GPIO y tramas ASCII viven en el driver y en ningún otro lado. `main.py` no debe importar `pyserial` jamás.
2. **Nada de lógica de negocio abajo del HAL.** El driver no decide si un peso es válido, no genera `event_id`, no habla con la nube. Devuelve una muestra cruda y ya.
3. **Un driver por marca/modelo**, seleccionable por variable de entorno (p. ej. `FIERRO_SCALE_DRIVER=gallagher-tsi2`). El campo tendrá marcas mezcladas.
4. **Cambiar de hardware no debe tocar la lógica de captura.** Si un PR cambia driver *y* `main.py`, la frontera está mal puesta — revisar antes de mergear.
5. **Sin hardware, falla ruidosa.** `SerialHardware` lanza `NotImplementedError` en vez de devolver datos falsos. Ese patrón es obligatorio.

## 2. Probar hardware sin hardware

El agente en la nube y CI **nunca** tienen báscula. Aun así, los drivers se prueban:

1. **Golden captures.** Grabar tráfico serial real del indicador a un archivo de fixture y reproducirlo en tests. Un driver se valida contra bytes reales, no contra suposiciones.
2. **Casos sucios obligatorios en los fixtures:** trama parcial, ruido, peso inestable, valor negativo, unidades en libras, animal moviéndose, dos aretes seguidos.
3. **Simulador serial** (`socat`/pty virtual) para pruebas de integración locales.
4. **Banco HIL** — una Pi en oficina cableada a indicador y lector reales, para validar antes de campo. Es el único lugar donde `FIERRO_MOCK_HW=0` corre fuera del rancho.
5. En CI y Cloud Agents: siempre `FIERRO_MOCK_HW=1`.

## 3. Separación en el repositorio

El hardware **no vive en `apps/`**. Cuando arranque el diseño físico:

```
apps/            # software: device-agent, api, web
hardware/
  carrier-board/ # esquemático + PCB (KiCad), por revisión
  enclosure/     # mecánica, cortes, montaje
  bom/           # lista de materiales con número de parte y proveedor
  test-fixtures/ # capturas serial reales, banco de pruebas
  docs/          # notas de bring-up, manuales de indicador/lector
```

**Versionado distinto para cada mundo:**

| | Esquema | Ejemplo |
|---|---|---|
| Software | **SemVer** | `agent_version = 0.4.1` |
| Hardware | **Revisión** | `carrier rev-B` |

El device reporta **ambos** en el heartbeat (`agent_version` + `hw_rev`). Sin eso es imposible diagnosticar "solo falla en las estaciones viejas".

**Compatibilidad declarada:** el software declara con qué revisiones de hardware funciona y falla ruidosamente ante una desconocida. Nunca asumir la más nueva.

## 4. Cuándo diseñar una PCB propia (y cuándo no)

Aplicar pragmatismo: **una PCB propia es una puerta de una sola vía** — fabricada, ya se pagó.

| Etapa | Qué usar |
|---|---|
| Sprint 0–1 | HATs comerciales + cableado. Nada de PCB propia |
| Validado en campo ≥ 1 sprint | Recién ahí, PCB propia si el cableado es el problema |
| Producción | Carrier propia (idealmente CM4/CM5), con rev y BOM controlados |

**Requisitos para abrir el ticket de PCB:**

- El prototipo cableado ya corrió en campo y se sabe exactamente qué integra.
- La lista de señales y protecciones está cerrada.
- Hay presupuesto de fabricación y ensamble.

## 5. Qué debe resolver la PCB propia

Cuando llegue, la carrier existe para resolver justo lo que rompe en campo:

1. **Entrada de energía robusta:** 12 V del rancho → buck; fusible, protección de polaridad inversa, TVS.
2. **UPS integrada con señal de corte** al SoC (ver [`edge-reliability.md`](edge-reliability.md) §2).
3. **RTC con batería** — resuelve el problema del reloj de raíz.
4. **Serial aislado galvánicamente** hacia indicador y lector: tierras distintas en un corral producen bucles y quema de puertos.
5. **Protección de línea** (TVS/supresores) en cada cable que sale del gabinete.
6. **Conectores industriales con clave y retención** (M12 o similar). Un jumper suelto en una manga es una falla garantizada.
7. **Watchdog externo** opcional si el del SoC no basta.
8. **Puntos de prueba y LEDs de diagnóstico**: energía, LTE, captura. El técnico en campo no trae laptop.

## 6. Proceso de diseño de PCB

```
Requisitos (señales + protecciones) → Esquemático → Revisión de pares
→ Layout → Revisión DFM → Fabricar lote pequeño → Bring-up con checklist
→ Validación en campo → Congelar revisión → BOM y documentación
```

- **Herramienta por defecto: KiCad** (formatos abiertos, versionables en git). Si el equipo decide otra, se documenta como decisión abierta.
- **Diseñar contra IPC:** IPC-2221 (general), IPC-2152 (anchos de pista por corriente), IPC-7351 (footprints), IPC-A-610 (aceptación de ensamble).
- **Commitear fuentes, no solo exportaciones.** Gerbers y PDFs son artefactos por revisión; el esquemático es la verdad.
- **Checklist de bring-up escrito antes de recibir la placa**, no improvisado con la placa en la mano.
- **Cada revisión lleva registro de cambios** y qué falla de campo corrige.

## 7. Tickets: hardware y software se separan

- Etiquetas distintas: `hardware`, `pcb`, `enclosure` vs `edge`, `api`, `web`.
- Un ticket **nunca** mezcla "diseñar la PCB" con "escribir el driver": distinto lead time, distinto riesgo, distinta persona.
- Los tickets de hardware llevan **lead time explícito** (fabricación y envío son semanas) — planificarlos con un sprint de anticipación. Ver [`sprints.md`](sprints.md).
- El software **nunca** se bloquea esperando hardware: se trabaja contra el HAL con fixtures. Si aun así se estanca, ver [`unblock.md`](unblock.md).

## Relacionados

- [`engineering-rules.md`](engineering-rules.md) — pilares y estándares industriales
- [`edge-reliability.md`](edge-reliability.md) — supervivencia en campo
- [`../architecture.md`](../architecture.md) — BOM por estación
