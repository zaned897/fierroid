# Fierro IoT — Sistema de pesaje de vacas

## Objetivo

Capturar **siempre** el peso de cada animal identificado por arete RFID, en el momento del pesaje, y sincronizarlo a la nube vía conectividad celular (Sixfab). Escala objetivo: miles de dispositivos en campo.

Principio no negociable: **la lectura se guarda en el dispositivo antes de intentar subirla**. La nube puede fallar; el corral no.

---

## Arquitectura lógica

```
[Arete RFID ISO11784/85] → [Lector panel LF] ─┐
                                              ├→ [Raspberry Pi agent] → SQLite outbox → MQTT/HTTPS → [API nube]
[Pesa industrial]        → [Indicador RS232] ─┘                                              │
                                                                                              ▼
                                                                                    Postgres / Timescale
                                                                                              │
                                                                                    PWA móvil (web)
```

### Capas

| Capa | Rol | Fallo aceptable |
|------|-----|-----------------|
| Edge (RPi) | Leer RFID + peso, asociar, persistir, reintentar sync | Solo hardware / energía |
| Transporte | Sixfab LTE (ECM/QMI), Wi‑Fi opcional | Sí → cola local |
| Ingest | MQTT + API HTTP idempotente | Sí → reintento edge |
| Datos | Pesajes, animales, dispositivos | Replicas / backups |
| Cliente | PWA móvil: ver pesajes, estado del device | Sí |

---

## Hardware recomendado (BOM por estación)

### Computación y conectividad

| Pieza | Recomendación | Notas |
|-------|---------------|-------|
| SBC | Raspberry Pi 4 (4GB) o Pi 5 | Pi 5 más margen; Pi 4 suficiente y más barato a escala |
| Modem | Sixfab Base HAT + modem LTE regional (o kit 4G/LTE) | **No depender de Sixfab CORE** (discontinuado 2025-12-31). Usar ECM/QMI |
| SIM | Sixfab IoT SIM o carrier local M2M | Preferir APN estable y roaming controlado |
| Antena | LTE externa + cable | Crucial en corrales metálicos |
| Almacenamiento | microSD industrial o NVMe (Pi 5) | Preferir industrial; considerar USB boot |
| Energía | 12V campo → buck 5V + UPS HAT / LiFePO4 | Sin UPS = lecturas perdidas en cortes |
| Gabinete | IP65 + ventilación / calefacción según clima | Polvo, humedad, sol |

### Identificación animal

| Pieza | Recomendación | Notas |
|-------|---------------|-------|
| Aretes | LF 134.2 kHz FDX-B / HDX (ISO 11784/11785) | Estándar ganadero; no UHF genérico |
| Lector | Panel fijo en manga / báscula (RS232/RS485) | Alcance ~30–90 cm según antena |
| Montaje | Antena a altura de cabeza/oreja en el pasillo | Evitar lecturas cruzadas de dos animales |

### Pesa

| Pieza | Recomendación | Notas |
|-------|---------------|-------|
| Plataforma | Báscula ganadera de tercero (Tru-Test, Gallagher, etc.) | No reinventar la celda de carga |
| Indicador | Con **salida continua / estable** por RS232 o USB-serial | Protocolo ASCII o frame fijo documentado |
| Interfaz a RPi | USB-RS232 o RS232→TTL (si GPIO UART) | Aislar galvanicamente si es posible |

**Trabajo pendiente con el proveedor de la pesa:** obtener el manual del indicador (baud, framing, comando de “peso estable”, si emite stream continuo o hay que poll). El agent en Python debe tener un *driver* por marca.

---

## Software en el dispositivo (edge)

Stack: **Python 3.12 + systemd**, proceso único supervisado.

### Flujo de captura (crítico)

1. Detectar RFID válido (debounce / hold time).
2. Esperar **peso estable** del indicador (umbral kg + tiempo mínimo quieto).
3. Crear evento `{device_id, tag_id, weight_kg, captured_at, event_id}`.
4. **Escribir en SQLite (WAL) de inmediato** — commit local = éxito de captura.
5. Encolar en outbox `pending`.
6. Publicar MQTT (o POST HTTPS) cuando haya red; marcar `synced` solo con ACK del broker/API.
7. Reintentos con backoff; nunca borrar `pending` sin ACK.

### Por qué SQLite + outbox

- Miles de devices: cada uno es autónomo.
- LTE intermitente en campo.
- Idempotencia por `event_id` (UUID v7 o hash estable) evita duplicados al reenviar.

### Simulación sin hardware

`FIERRO_MOCK_HW=1` genera RFID + pesos para desarrollo y CI.

---

## Nube y sync

| Componente | MVP | Escala |
|------------|-----|--------|
| Ingest | HTTPS batch + MQTT opcional | MQTT (EMQX / AWS IoT) + TLS mTLS |
| API | FastAPI | Mismo + workers |
| DB | SQLite/Postgres local dev | Postgres + Timescale hypertables |
| Auth | API keys por device / JWT usuario | mTLS devices + OIDC usuarios |
| Observabilidad | logs + heartbeat device | métricas cola, lag sync, uptime |

Sixfab aporta **conectividad IP**; el broker/API es nuestro (o cloud managed). No acoplar lógica de negocio a un portal de Sixfab.

---

## Cliente móvil

**Recomendación MVP: PWA web responsive (no app nativa).**

Razones:

- Un solo codebase; distribuible por URL.
- Actualizaciones sin stores.
- Suficiente para listar pesajes, estado del device y alertas.
- Si más adelante hace falta Bluetooth local / offline profundo → Capacitor o app nativa.

---

## Fiabilidad a escala (miles de devices)

1. **Captura local primero** — métrica de éxito = eventos en SQLite, no en la nube.
2. **Idempotencia** en ingest.
3. **Heartbeat** cada N minutos (batería, cola pendiente, versión SW, señal).
4. **OTA** controlado (imagen A/B o paquetes firmados); no auto-update ciego en todos a la vez.
5. **Drivers de pesa/RFID plugables** — el campo tendrá marcas distintas.
6. **Pruebas de chaos**: cortar LTE, reiniciar mid-pesaje, doble RFID.
7. **Capacidad de cola**: dimensionar SD para semanas de pesajes offline.

---

## Roadmap por fases

### Fase 0 — Ahora (este repo)

- Agent con mock HW + outbox SQLite
- API ingest + listado
- PWA mínima
- Docs de BOM y contratos de datos

### Fase 1 — Prototipo físico (1–3 estaciones)

- Integrar 1 indicador real (RS232)
- Integrar 1 lector panel RFID
- Sixfab LTE en ECM + sync real
- Gabinete + UPS

### Fase 2 — Optimización (meses 1–N)

- Estabilidad de peso, anti-doble lectura
- Dashboard ops (cola, devices offline)
- Multi-tenant / multi-rancho

### Fase 3 — Flota

- Provisioning masivo, OTA, alertas, SLOs de “0 lecturas perdidas”

---

## Decisiones abiertas (para validar contigo)

1. País/región del despliegue → bandas LTE y carrier.
2. Marca/modelo exacto de la báscula e indicador.
3. ¿Aretes ya instalados? ¿FDX-B, HDX o ambos?
4. ¿Un rancho o multi-cliente SaaS desde el día 1?
5. ¿Necesitan ver el peso en vivo en el celular durante el pesaje (latencia LTE) o basta sync diferido?
