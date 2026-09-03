# Testing y evidencia

Expectativas de calidad para cambios en Fierro IoT.

## Comandos estándar

```bash
source .venv/bin/activate

# Python
ruff check apps scripts
pytest apps/device-agent apps/api -q

# Web (si hubo cambios en apps/web)
cd apps/web && pnpm lint && pnpm build
```

Instalar deps: `./scripts/install-deps.sh`

## Qué debe probarse

| Tipo de cambio | Mínimo |
|----------------|--------|
| device-agent | pytest store/hardware; manual mock si lógica de captura/sync |
| api | pytest test_api; curl POST/GET idempotente |
| web | eslint + build; manual PWA si UI cambió |
| docs only | Revisión de links; no tests obligatorios |
| scripts / env | Ejecutar install script dos veces (idempotente) |

## Pruebas contra Postgres

Las pruebas de `store_pg.py` se saltan solas si no hay DSN. Para correrlas:

```bash
docker compose up -d db
FIERRO_TEST_PG_DSN=postgresql://fierro:fierro@localhost:5432/fierro   pytest apps/api -q
```

CI las corre siempre: el job `python` levanta un servicio Postgres y define esa
variable. Si tu PR toca el store y las ves como `skipped` en local, no asumas
que pasan.

## Entorno completo en Docker

```bash
docker compose up --build          # db + migraciones + api + agent mock
docker compose --profile tools run --rm seed   # datos sinteticos historicos
docker compose down -v             # borra tambien los volumenes
```

CI corre este mismo stack en el job `compose`: build, health de la API, siembra
y verificacion de que las lecturas quedaron persistidas.

## Flujo manual de referencia (hello-world)

```bash
# Terminal 1
FIERRO_API_DB_PATH=/tmp/fierro-api.db fierro-api

# Terminal 2
FIERRO_MOCK_HW=1 FIERRO_API_URL=http://127.0.0.1:8000 \
  FIERRO_DB_PATH=/tmp/fierro-device.db fierro-device

# Terminal 3
cd apps/web && pnpm dev
# → http://127.0.0.1:5173 — deben aparecer lecturas y heartbeat
```

Verificar outbox local:

```bash
sqlite3 /tmp/fierro-device.db \
  "SELECT event_id, tag_id, weight_kg, status FROM readings ORDER BY created_at DESC LIMIT 5;"
```

## Invariantes que no deben romperse

1. **Outbox:** `save_reading` → fila `pending` antes de sync.
2. **Sync:** solo `synced` tras ACK de API.
3. **API:** re-POST mismo `event_id` → una fila, respuesta 200.
4. **Mock:** Cloud Agent siempre `FIERRO_MOCK_HW=1` (sin serial real).

## Evidencia en PRs

- Cambios de UI: screenshot o video corto del flujo.
- Cambios de API/agent: salida de pytest + ejemplo curl/json.
- No presentar tests fallidos como "parcialmente OK".

## Tests nuevos

Agregar tests cuando:

- El usuario lo pida.
- Se corrige un bug reproducible.
- Se toca lógica crítica (outbox, ingest idempotente) sin cobertura.

No agregar tests triviales que solo assertan getters obvios.

## CI

[`.github/workflows/ci.yml`](../../.github/workflows/ci.yml) corre en cada PR y en push a `main`:

| Job | Que valida |
|-----|------------|
| `python` | `ruff check apps scripts` + `pytest` con servicio Postgres real |
| `web` | `pnpm lint` + `pnpm build` con lockfile congelado |
| `compose` | Build de imagenes, health de la API, siembra sintetica y persistencia |

`FIERRO_MOCK_HW=1` esta fijado a nivel workflow: ningun job toca hardware.

Correr los mismos comandos en local antes del push sigue siendo lo esperado; CI
es la red de seguridad, no el primer lugar donde te enteras.
