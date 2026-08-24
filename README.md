# Fierro IoT

Sistema de **pesaje de ganado** edge-first: asocia el arete RFID de cada animal con su peso en el momento del pesaje, guarda la lectura en el dispositivo (Raspberry Pi) y la sincroniza a la nube por LTE (Sixfab).

**Principio no negociable:** la lectura se confirma al escribir en SQLite local. La nube puede fallar; el corral no. Diseñado para **miles de estaciones** en campo.

---

## Qué hace (hoy)

1. El **device agent** (RPi o mock) lee RFID + peso estable.
2. Persiste el evento en una **outbox SQLite** (`pending` → `synced`).
3. Sincroniza por HTTP a la **API** (ingest idempotente por `event_id`).
4. La **PWA** muestra dispositivos (heartbeat) y últimas lecturas en móvil.

Sin hardware real usa `FIERRO_MOCK_HW=1` para simular aretes y pesos.

```
[Arete RFID ISO11784/85] → [Lector panel] ─┐
                                           ├→ [RPi agent] → SQLite → LTE → [API] → [PWA]
[Pesa industrial]        → [Indicador RS232]─┘
```

Docs de detalle:

- [`docs/architecture.md`](docs/architecture.md) — BOM, fiabilidad, roadmap
- [`docs/data-contract.md`](docs/data-contract.md) — contrato de eventos
- [`AGENTS.md`](AGENTS.md) — notas para Cloud Agents

---

## Tech stack

| Capa | Tecnología | Notas |
|------|------------|--------|
| Edge | Python 3.12, pyserial, httpx, SQLite WAL | Servicio systemd en RPi |
| Hardware (objetivo) | RPi 4/5, Sixfab Base HAT + LTE, lector LF 134.2 kHz, báscula 3.º | Drivers serial plugables |
| Conectividad | Sixfab LTE (ECM/QMI), Wi‑Fi opcional | **No** Sixfab CORE (discontinuado) |
| API | FastAPI, Pydantic, Uvicorn | Ingest + heartbeats + listado |
| Persistencia cloud (MVP) | SQLite en API | Postgres/Timescale en sprints siguientes |
| Sync | HTTPS batch (MQTT opcional después) | Idempotencia por `event_id` |
| Frontend | React 19, Vite 6, PWA | UI mobile-first |
| Tooling | uv, pnpm, ruff, pytest, ESLint | `scripts/install-deps.sh` |
| Cloud Agents | `.cursor/Dockerfile` + `environment.json` | Install idempotente con uv |

### Monorepo

| App | Path | Rol |
|-----|------|-----|
| Device agent | `apps/device-agent` | Captura + outbox + sync |
| API | `apps/api` | Ingest y consulta |
| Web PWA | `apps/web` | Vista móvil de pesajes |

---

## Setup

### Requisitos

- Python 3.12+
- Node.js 22+ y pnpm
- (Opcional) `curl` para instalar [uv](https://github.com/astral-sh/uv) vía el script

### Instalación rápida

```bash
./scripts/install-deps.sh
source .venv/bin/activate
```

El script crea `.venv` con **uv**, instala `fierro-device` + `fierro-api` + deps de test, y corre `pnpm install` en `apps/web`.

### Correr en local (sin hardware)

```bash
source .venv/bin/activate

# Terminal 1 — API
FIERRO_API_DB_PATH=/tmp/fierro-api.db fierro-api

# Terminal 2 — agent mock
FIERRO_MOCK_HW=1 \
FIERRO_API_URL=http://127.0.0.1:8000 \
FIERRO_DB_PATH=/tmp/fierro-device.db \
FIERRO_DEVICE_ID=rpi-dev-001 \
fierro-device

# Terminal 3 — PWA
cd apps/web && pnpm dev
```

Abrir `http://127.0.0.1:5173`.

### Lint / test / build

```bash
source .venv/bin/activate
ruff check apps
pytest apps/device-agent apps/api -q
cd apps/web && pnpm lint && pnpm build
```

### Variables de entorno útiles

| Variable | Default | Uso |
|----------|---------|-----|
| `FIERRO_MOCK_HW` | `1` | `1` = simulación; `0` = serial real (WIP) |
| `FIERRO_DEVICE_ID` | `rpi-dev-001` | ID de la estación |
| `FIERRO_DB_PATH` | `/tmp/fierro-device.db` | Outbox del agent |
| `FIERRO_API_URL` | `http://127.0.0.1:8000` | Destino de sync |
| `FIERRO_API_DB_PATH` | `/tmp/fierro-api.db` | DB de la API |
| `FIERRO_SCALE_PORT` / `FIERRO_RFID_PORT` | `/dev/ttyUSB*` | Puertos seriales reales |

---

## Sprints iniciales

### Sprint 0 — Base de software (hecho / en curso)

- [x] Monorepo agent + API + PWA
- [x] Outbox SQLite + ingest idempotente
- [x] Mock de hardware y hello-world end-to-end
- [x] Docs de arquitectura y contrato de datos
- [ ] Auth mínima (API key por device / JWT usuario)
- [ ] CI (lint + test en PR)

### Sprint 1 — Primer prototipo físico (1–3 estaciones)

- Integrar **1 indicador de báscula** real (protocolo RS232 documentado)
- Integrar **1 lector panel RFID** LF ISO 11784/85
- Sixfab LTE en ECM + sync real en campo
- Gabinete IP65 + UPS; validar “0 lecturas perdidas” con cortes de red
- Dashboard ops básico: cola `pending`, último heartbeat, versión agent

### Sprint 2 — Confiabilidad de captura

- Filtro de peso estable (umbral + tiempo quieto) calibrado en manga
- Debounce / anti doble lectura (mismo tag, dos animales cerca)
- Heartbeat enriquecido (señal LTE, disco, temperatura)
- Pruebas de chaos: reinicio mid-pesaje, LTE off, SD llena
- Migrar API a Postgres (preparar Timescale para series)

### Sprint 3 — Producto usable en rancho

- Multi-rancho / multi-usuario en PWA
- Historial por animal (`tag_id`), gráficos de ganancia de peso
- Alertas (device offline, cola alta, sync fallando)
- Provisioning de devices (ID, credenciales, OTA planificado)
- MQTT broker (EMQX / IoT Core) como camino principal de ingest a escala

### Sprint 4 — Flota

- OTA A/B o paquetes firmados; rollout gradual
- Observabilidad (métricas de lag, uptime, tasa de sync)
- SLOs: captura local ≥ 99.9%; sync eventual documentado
- Costeo SIM / datos por device

---

## Puntos a mejorar

### Críticos (bloquean campo real)

1. **Drivers serial reales** — hoy `SerialHardware` lanza `NotImplementedError`; falta protocolo por marca de indicador y lector.
2. **Energía y gabinete** — sin UPS/IP65 las lecturas se pierden por cortes y polvo/humedad.
3. **Auth y tenancy** — API abierta en MVP; no apta para internet pública.
4. **Persistencia cloud** — SQLite de API no escala; migrar a Postgres pronto.

### Importantes (calidad / operación)

5. **MQTT + mTLS** — HTTPS batch alcanza para prototipo; flota de miles prefiere broker con backpressure.
6. **Observabilidad** — logs estructurados, métricas de cola y fallos de sync, alertas.
7. **OTA y versionado** — actualizar miles de RPi sin brickear ni perder outbox.
8. **PWA** — offline ligero, push de alertas, UX de “pesaje en vivo” vs sync diferido.
9. **CI/CD** — pipeline en cada PR; builds reproducibles de imagen RPi.
10. **Pruebas de campo** — lecturas cruzadas, tags sucios, animales inquietos, corrales metálicos (LTE/RFID).

### Deuda técnica conocida

- Sync solo HTTP; MQTT pendiente.
- Sin isolation fuerte de DB en proceso largo de API (tests ya usan DB temporal).
- UI mínima (lista); falta detalle por animal y filtros.
- Documentar runbook de Sixfab ECM por región/carrier.

---

## Decisiones abiertas

1. País / región → bandas LTE y carrier (o Sixfab SIM).
2. Marca/modelo exacto de báscula e indicador.
3. Aretes ya instalados: ¿FDX-B, HDX o ambos?
4. ¿Un rancho o multi-cliente SaaS desde el día 1?
5. ¿Peso en vivo en el celular (latencia LTE) o basta sync diferido?

---

## Contribución rápida

1. Leer `docs/architecture.md`.
2. `./scripts/install-deps.sh` y levantar mock (sección Setup).
3. Cambios pequeños y testeados (`ruff` + `pytest` + lint web).
4. Mantener el invariante: **captura local antes que sync**.
