---
name: fierro-dev-workflow
description: "How to work on the Fierro IoT cattle weighing monorepo: principles, local services, scope, and what to avoid. Use before implementing features in device-agent, api, or web."
---

# Fierro dev workflow

Read the full guide: [`docs/agent/workflow.md`](../../../docs/agent/workflow.md)

## When to use

- Starting any non-trivial task in this repo
- Unsure which app to change (edge vs API vs PWA)
- Setting up local dev or Cloud Agent session

## Quick rules

1. **Edge-first:** capture success = SQLite commit on device before cloud sync
2. **Idempotent ingest:** same `event_id` must not duplicate API rows
3. **Minimal diff** matching existing conventions
4. **Always run:** `ruff check apps`, `pytest apps/device-agent apps/api -q`, web lint/build if UI touched
5. **No hardware in cloud:** `FIERRO_MOCK_HW=1`

## Local services

```bash
./scripts/install-deps.sh && source .venv/bin/activate
fierro-api   # :8000
FIERRO_MOCK_HW=1 FIERRO_API_URL=http://127.0.0.1:8000 FIERRO_DB_PATH=/tmp/fierro-device.db fierro-device
cd apps/web && pnpm dev   # :5173
```

## Related docs

- [`docs/agent/README.md`](../../../docs/agent/README.md) — index
- [`docs/architecture.md`](../../../docs/architecture.md) — product architecture
- [`AGENTS.md`](../../../AGENTS.md) — Cloud Agent specifics
