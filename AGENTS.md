## Agent documentation

Guías de trabajo (flujo, PRs, Jira, tests): **[`docs/agent/README.md`](docs/agent/README.md)**

Skills equivalentes en `.cursor/skills/`: `fierro-dev-workflow`, `fierro-pull-requests`, `fierro-jira`.

---

## Cursor Cloud specific instructions

### Product scope

Monorepo Fierro IoT: `apps/device-agent` (edge/RPi), `apps/api` (FastAPI ingest), `apps/web` (Vite PWA). Architecture: `docs/architecture.md`.

### Dev services (local / cloud agent)

1. Activate venv: `source /workspace/.venv/bin/activate` (created by install/update script).
2. API: `fierro-api` (binds `0.0.0.0:8000`). Data file default: `/tmp/fierro-api.db`.
3. Device mock: `FIERRO_MOCK_HW=1 FIERRO_API_URL=http://127.0.0.1:8000 FIERRO_DB_PATH=/tmp/fierro-device.db fierro-device`
4. Web: `cd apps/web && pnpm dev --host 0.0.0.0 --port 5173`

No Docker required for the MVP path (HTTP ingest + SQLite). MQTT is optional later.

### Lint / test / build

- Python: `ruff check apps` and `pytest apps/device-agent apps/api -q`
- Web: `cd apps/web && pnpm lint && pnpm build`

Details: [`docs/agent/testing.md`](docs/agent/testing.md)

### PRs and Jira

- PRs: [`docs/agent/pull-requests.md`](docs/agent/pull-requests.md) — branch `cursor/<name>-7dff` → `main`
- Jira: [`docs/agent/jira.md`](docs/agent/jira.md) — templates and Atlassian MCP

### Gotchas

- Hardware serial drivers are mocked unless `FIERRO_MOCK_HW=0` and ports are configured; cloud VMs have no scale/RFID — always use mock for CI/agents.
- Idempotent ingest: re-POSTing the same `event_id` must not duplicate rows.
- Prefer not killing long-running `fierro-api` / `pnpm dev` between agent turns; leave them running.
