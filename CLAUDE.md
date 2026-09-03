# Fierro IoT — contexto para agentes Claude Code

Sistema de pesaje de ganado edge-first. Monorepo: `apps/device-agent` (RPi), `apps/api`
(FastAPI ingest), `apps/web` (PWA Vite). Producto y setup: [`README.md`](README.md).

## Invariante raíz

> **Ninguna lectura de pesaje se pierde.** Todo lo demás es negociable.

Commit local en la outbox SQLite = éxito de captura. La nube puede fallar; el corral no.

## Reglas no negociables

1. **Falla ruidosa, nunca datos falsos.** Patrón del repo: `SerialHardware.read()` lanza
   `NotImplementedError` en vez de devolver un peso inventado.
2. **Idempotencia** por `event_id`. Nada pasa a `synced` sin ACK del servidor.
3. **Diff mínimo**, dentro del alcance del ticket. Refactor fuera de alcance = ticket aparte.
4. **Atascado no es insistir.** Tras 3 intentos o ~45 min sin avance, aplicar `fierro-unblock`.
5. **Sin hardware en CI ni agentes:** `FIERRO_MOCK_HW=1`.

## Skills del repo

En `.claude/skills/` (espejo de `.cursor/skills/`). Cargar la que aplique **antes** de implementar:

| Skill | Cuándo |
|-------|--------|
| `fierro-anti-vibe-coding` | **Antes de escribir cualquier función.** Buscar en el grafo, contrato primero |
| `fierro-product-principles` | **Antes de escribir código.** UI, contrato de datos, bugs, releases |
| `fierro-engineering-rules` | Cualquier cambio no trivial o decisión de diseño |
| `fierro-edge-reliability` | Device agent, storage, energía, systemd, deploy a RPi |
| `fierro-hardware-boundary` | Drivers serial, RFID/báscula, PCB, gabinete, BOM |
| `fierro-unblock` | Desarrollo estancado |
| `fierro-sprints` | Planear, partir trabajo, abrir o cerrar tickets |
| `fierro-dev-workflow` | Flujo general |
| `fierro-pull-requests` | Ramas y PRs |
| `fierro-jira` | Tickets |

Contenido canónico y extendido: [`docs/agent/README.md`](docs/agent/README.md).
Notas de Cloud Agents: [`AGENTS.md`](AGENTS.md).

## Comandos

```bash
./scripts/install-deps.sh && source .venv/bin/activate
pre-commit install            # gate local, una vez
ruff check apps scripts
pytest apps/device-agent apps/api -q
cd apps/web && pnpm lint && pnpm build   # solo si tocaste web
```

## Al editar las skills

`.cursor/skills/` y `.claude/skills/` son espejos idénticos. Tras editar uno:

```bash
rm -rf .claude/skills && cp -r .cursor/skills .claude/skills
```
