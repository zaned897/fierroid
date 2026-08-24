# Fierro IoT — pesaje de ganado

Sistema edge-first para asociar **RFID de arete + peso** en Raspberry Pi, persistir localmente sin pérdida, y sincronizar a la nube (Sixfab LTE + API/MQTT).

## Documentación

- Arquitectura, BOM y roadmap: [`docs/architecture.md`](docs/architecture.md)
- Contrato de eventos: [`docs/data-contract.md`](docs/data-contract.md)

## Monorepo

| App | Path | Rol |
|-----|------|-----|
| Device agent | `apps/device-agent` | Corre en RPi: lee HW (o mock), SQLite outbox, sync |
| API | `apps/api` | Ingest idempotente + consulta de pesajes |
| Web PWA | `apps/web` | UI móvil para ver pesajes y estado |

## Desarrollo local (sin hardware)

```bash
# Dependencias Python
python3 -m venv .venv
source .venv/bin/activate
pip install -e apps/device-agent -e apps/api
pip install -r requirements-dev.txt

# Web
cd apps/web && pnpm install && cd ../..

# Terminal 1 — API
fierro-api

# Terminal 2 — agent mock (genera pesajes)
FIERRO_MOCK_HW=1 FIERRO_API_URL=http://127.0.0.1:8000 fierro-device

# Terminal 3 — PWA
cd apps/web && pnpm dev
```

Abrir `http://127.0.0.1:5173`.

## Tests / lint

```bash
source .venv/bin/activate
ruff check apps
pytest apps/device-agent apps/api -q
cd apps/web && pnpm lint && pnpm build
```

## Principio de diseño

**La lectura se confirma al escribir en SQLite del device.** La nube es eventual.
