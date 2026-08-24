# Reglas de ingeniería — Fierro IoT

Reglas que **todo agente y humano** sigue al proponer o implementar cambios.
Complementan [`workflow.md`](workflow.md): eso es *cómo entregar*, esto es *cómo decidir*.

## Invariante raíz

> **Ninguna lectura de pesaje se pierde.**
> Todo lo demás — features, UI, refactors, nube — es negociable.

Si un cambio pone en riesgo este invariante, no entra, aunque el ticket lo pida.

## Los 5 pilares

| Pilar | Significa | No significa |
|---|---|---|
| **Pragmatismo** | La solución más simple que sobrevive al corral | Prototipo desechable |
| **Robustez** | Falla predecible, se recupera sola, no corrompe datos | Cero fallos |
| **Escalabilidad** | Contratos pensados para miles de estaciones desde el día 1 | Infra de miles el día 1 |
| **Estándares industriales** | Norma existente > invento propio | Certificar todo hoy |
| **Separación HW/SW** | El software no sabe de baudios; el hardware no sabe de negocio | Equipos separados |

---

## Pragmatismo — reglas duras

1. **Vertical slice antes que capa completa.** Un pesaje real de punta a punta vale más que un ORM perfecto.
2. **Comprar > construir.** Celdas de carga, indicadores, aretes y módems se compran. Nuestro valor es la captura confiable y los datos, no reinventar una báscula.
3. **Tecnología aburrida por defecto.** SQLite, systemd, HTTP, Postgres. Cada pieza exótica necesita justificación escrita en un ticket.
4. **Puertas de una vía vs de dos vías.**
   - Reversible (nombre de campo interno, layout de UI, refactor local) → decide y avanza.
   - Irreversible (contrato de datos ya desplegado, esquema de `device_id`, rev de PCB fabricada, elección de carrier) → ticket con opciones + aprobación del usuario.
5. **YAGNI, excepto en las fronteras.** No abstraigas lógica de negocio "por si acaso". **Sí** deja interfaz en drivers de hardware, transporte de sync y persistencia cloud: ahí ya sabemos que habrá más de una implementación.
6. **Diff mínimo.** Refactor fuera del alcance del ticket = ticket aparte.
7. **Si tarda más de lo previsto, no insistas en silencio.** Ver [`unblock.md`](unblock.md).

## Robustez — reglas duras

1. **Falla ruidosa, nunca datos falsos.** Precedente del repo: `SerialHardware.read()` lanza `NotImplementedError` en vez de devolver un peso inventado. Copiar ese patrón siempre.
2. **Toda operación de red puede fallar.** Timeout explícito, reintento con backoff **y jitter**, y estado local que sobreviva al fallo.
3. **Idempotencia en todo lo que cruza la red.** `event_id` es la llave; reenviar nunca duplica.
4. **Nada se borra ni se marca `synced` sin ACK** del servidor.
5. **El proceso se puede matar en cualquier línea.** Diseña asumiendo `SIGKILL` entre dos instrucciones — eso es exactamente un apagón. Detalle: [`edge-reliability.md`](edge-reliability.md).
6. **Estados observables.** Cola pendiente, última sync, versión, salud del device: en el heartbeat. Lo que no se mide, no existe.
7. **Degradar, no morir.** Sin LTE → seguir capturando. Sin RFID → registrar peso con `tag_id` nulo y marcarlo, nunca descartar el evento en silencio.

## Escalabilidad — reglas duras

Objetivo declarado: **miles de estaciones**. Lo que se diseña hoy no debe romperse a esa escala.

1. **Device autónomo.** Ningún device depende de otro ni de sesión con estado en la nube.
2. **API sin estado.** Toda la verdad vive en la DB, nada en memoria del worker.
3. **Jitter obligatorio en reintentos.** Cuando una torre LTE regresa, *todas* las estaciones de esa zona reconectan el mismo segundo. Backoff exponencial **+ jitter aleatorio**, o tumbamos nuestro propio ingest.
4. **Batch acotado y con backpressure.** Tamaño de lote con límite; si el servidor responde `429`/`503`, respetarlo — no insistir más fuerte.
5. **Identidad por device desde el día 1.** `device_id` + credencial propia. Una API key compartida por la flota obliga a tocar miles de equipos para rotarla.
6. **El costo por device es un requisito.** Datos LTE, almacenamiento y filas se multiplican por N. Un heartbeat cada 30 s × 5 000 devices = **14.4 M requests/día**. Dimensionar antes de subir frecuencias.
7. **Series temporales particionables.** Los pesajes son append-only con tiempo: Postgres + Timescale, particionado temporal.
8. **Compatibilidad de contrato N y N-1.** Los devices en campo tendrán versiones viejas por meses. Ver [`../data-contract.md`](../data-contract.md).

---

## Estándares industriales

Preferir norma existente sobre invención propia:

| Dominio | Estándar | Uso en Fierro |
|---|---|---|
| Identificación animal | **ISO 11784 / 11785** (LF 134.2 kHz, FDX-B / HDX) | Formato de `tag_id`; no UHF genérico |
| Conformidad de lectores | **ISO 24631** | Criterio para evaluar lectores panel |
| Pesaje no automático | **OIML R76** + transposición nacional | Si el peso se usa para compraventa, aplica metrología legal |
| Serial | **TIA/EIA-232-F**, **TIA/EIA-485-A** | Interfaz a indicador y lector |
| Bus de campo | **Modbus RTU** sobre RS-485 | Si el indicador lo soporta, preferirlo a ASCII propietario |
| Mensajería IoT | **MQTT 3.1.1 / 5** + **Sparkplug B** | Camino de ingest a escala |
| Seguridad OT | **IEC 62443** | Segmentación y credenciales de flota |
| Gabinete | **IEC 60529** (IP65/IP66), **NEMA 4X** | Selección de caja |
| EMC y transitorios | **IEC 61000-4-2 / -4-4 / -4-5** | Protección en líneas serial y alimentación |
| PCB | **IPC-2221**, **IPC-2152**, **IPC-7351**, **IPC-A-610** | Diseño, anchos de pista, footprints, aceptación |
| Tiempo | **ISO 8601 / RFC 3339** en UTC | `captured_at` siempre UTC con offset |
| Identificadores | **UUID v7 (RFC 9562)** | `event_id` ordenable por tiempo |
| Versionado SW | **SemVer 2.0.0** | `agent_version`, versión de API |

> **Pendiente de confirmar:** país de despliegue → norma metrológica aplicable (p. ej. NOM-010-SCFI en México) y bandas LTE. Sigue como decisión abierta en el [`README`](../../README.md).

---

## Checklist antes de abrir PR

Responder explícitamente en la descripción del PR:

- [ ] ¿Este cambio puede perder una lectura? ¿Por qué no?
- [ ] ¿Qué pasa si se corta la energía a mitad de esta operación?
- [ ] ¿Qué pasa si esto corre en 5 000 devices al mismo tiempo?
- [ ] ¿Existe un estándar industrial que ya resuelve esto?
- [ ] ¿El diff se mantuvo dentro del alcance del ticket?

## Relacionados

- [`edge-reliability.md`](edge-reliability.md) — supervivencia del device en campo
- [`hardware-boundary.md`](hardware-boundary.md) — frontera HW/SW y PCBs
- [`unblock.md`](unblock.md) — qué hacer cuando el desarrollo se estanca
- [`sprints.md`](sprints.md) — tickets y sprints
