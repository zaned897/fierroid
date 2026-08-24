# Cómo trabajar en Fierro IoT

Guía para humanos y agentes (Cursor Cloud Agent, IDE local).

## Antes de codear

1. Leer [`README.md`](../../README.md) y, si aplica, [`architecture.md`](../architecture.md).
2. Confirmar el **alcance** del pedido (¿solo docs? ¿edge? ¿API? ¿PWA?).
3. Revisar [`jira.md`](jira.md) si el trabajo viene de un ticket o debe generar uno.
4. Instalar deps: `./scripts/install-deps.sh` y `source .venv/bin/activate`.

## Principios de ingeniería (este repo)

| Prioridad | Regla |
|-----------|--------|
| 1 | **Edge-first:** éxito de captura = commit en SQLite del device |
| 2 | **Idempotencia:** mismo `event_id` no duplica filas en API |
| 3 | **Diff mínimo:** no refactorizar fuera del alcance |
| 4 | **Convenciones existentes:** Python FastAPI, React/Vite, ruff, pytest |
| 5 | **Probar en runtime:** lint + tests + flujo representativo |

## Flujo recomendado por tarea

```
Entender → Plan corto → Implementar → Lint/test → Evidencia → PR → (Jira si aplica)
```

### 1. Entender

- Trazar qué apps toca: `device-agent`, `api`, `web`.
- Sin hardware en CI/Cloud: usar `FIERRO_MOCK_HW=1`.

### 2. Implementar

- Un commit lógico por cambio (no mezclar refactor + feature sin pedirlo).
- No commitear `.venv`, `node_modules`, `*.db`, `.vite`, `*.egg-info`.

### 3. Validar

Ver [`testing.md`](testing.md). Mínimo:

```bash
source .venv/bin/activate
ruff check apps
pytest apps/device-agent apps/api -q
cd apps/web && pnpm lint && pnpm build   # si tocaste web
```

### 4. Entregar

- Push a rama feature (ver [`pull-requests.md`](pull-requests.md)).
- PR hacia `main` con descripción clara y checklist de pruebas.
- Actualizar ticket Jira si existe (estado, enlace al PR).

## Servicios locales

| Servicio | Comando |
|----------|---------|
| API | `FIERRO_API_DB_PATH=/tmp/fierro-api.db fierro-api` |
| Agent mock | `FIERRO_MOCK_HW=1 FIERRO_API_URL=http://127.0.0.1:8000 FIERRO_DB_PATH=/tmp/fierro-device.db fierro-device` |
| PWA | `cd apps/web && pnpm dev` |

No matar servicios en caliente entre turnos del agente salvo que haya conflicto de puerto.

## Qué evitar

- Depender de Sixfab CORE (discontinuado); usar ECM/QMI.
- Asumir hardware serial en Cloud Agent (implementar/mock).
- Cambios grandes de infra sin ticket o acuerdo (Postgres, MQTT, auth).
- Force push o amend salvo instrucción explícita.
- Mergear PRs automáticamente salvo que el usuario lo pida.

## Cuándo pedir acllaración al usuario

- Marca/modelo de báscula o lector RFID para drivers reales.
- Proyecto Jira / epic / credenciales Atlassian no configuradas.
- País, carrier LTE, multi-tenant vs single ranch.
- Cambios que afecten contrato en [`data-contract.md`](../data-contract.md) sin migración.

## Escalamiento por app

| Cambio | Archivos típicos |
|--------|------------------|
| Captura / outbox / sync | `apps/device-agent/src/fierro_device/*` |
| Ingest / API REST | `apps/api/src/fierro_api/*` |
| UI móvil | `apps/web/src/*` |
| Producto / BOM / sprints | `docs/*`, `README.md` |
| Entorno Cloud Agent | `.cursor/*`, `scripts/install-deps.sh`, `AGENTS.md` |
