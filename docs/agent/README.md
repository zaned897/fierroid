# Guías para agentes (Cursor / Cloud Agent)

Documentación de **cómo trabajar en Fierro IoT**: flujo de desarrollo, PRs, Jira, pruebas y convenciones del repo.

Los agentes deben leer esto **antes** de implementar cambios no triviales.

## Índice

### Cómo decidir

| Documento | Contenido |
|-----------|-----------|
| [`product-principles.md`](product-principles.md) | **Empieza aquí.** Elegancia sobre estado del arte, multi-idioma, entrega por etapas, causa raíz, diseño, LoRaWAN |
| [`engineering-rules.md`](engineering-rules.md) | Pilares: pragmatismo, robustez, escala, estándares industriales |
| [`edge-reliability.md`](edge-reliability.md) | Que la RPi no falle: apagones, corrupción de SD, watchdog, reloj, OTA |
| [`hardware-boundary.md`](hardware-boundary.md) | Frontera HW/SW, drivers, PCBs propias, versionado de revisiones |
| [`unblock.md`](unblock.md) | Qué hacer cuando el desarrollo se estanca; alternativas y escalación |

### Cómo entregar

| Documento | Contenido |
|-----------|-----------|
| [`workflow.md`](workflow.md) | Principios, flujo diario, qué hacer / qué no hacer |
| [`sprints.md`](sprints.md) | Cadencia, granularidad de tickets, Definition of Ready / Done |
| [`pull-requests.md`](pull-requests.md) | Ramas, commits, PRs, merge a `main` |
| [`jira.md`](jira.md) | Cuándo abrir tickets, plantillas, duplicados, Atlassian MCP |
| [`testing.md`](testing.md) | Lint, tests, evidencia, mock hardware |

## Skills en el repo

Mismo contenido en formato skill, para que **cualquier agente** las cargue por sí solo:

- `.cursor/skills/` — Cursor
- `.claude/skills/` — Claude Code

Ambos directorios son **espejos idénticos**. Al editar uno, sincronizar el otro:

```bash
rm -rf .claude/skills && cp -r .cursor/skills .claude/skills
```

| Skill | Uso |
|-------|-----|
| [`fierro-product-principles`](../../.cursor/skills/fierro-product-principles/SKILL.md) | Principios de producto: cómo se construye aquí |
| [`fierro-engineering-rules`](../../.cursor/skills/fierro-engineering-rules/SKILL.md) | Reglas de ingeniería y estándares |
| [`fierro-edge-reliability`](../../.cursor/skills/fierro-edge-reliability/SKILL.md) | Confiabilidad del device en campo |
| [`fierro-hardware-boundary`](../../.cursor/skills/fierro-hardware-boundary/SKILL.md) | Separación hardware / software y PCBs |
| [`fierro-unblock`](../../.cursor/skills/fierro-unblock/SKILL.md) | Desbloqueo y alternativas |
| [`fierro-sprints`](../../.cursor/skills/fierro-sprints/SKILL.md) | Sprints, tickets, DoR / DoD |
| [`fierro-dev-workflow`](../../.cursor/skills/fierro-dev-workflow/SKILL.md) | Flujo general de trabajo |
| [`fierro-pull-requests`](../../.cursor/skills/fierro-pull-requests/SKILL.md) | Crear y actualizar PRs |
| [`fierro-jira`](../../.cursor/skills/fierro-jira/SKILL.md) | Tickets en Jira |

## Contexto del producto

- README: [`../../README.md`](../../README.md)
- Arquitectura: [`../architecture.md`](../architecture.md)
- Contrato de datos: [`../data-contract.md`](../data-contract.md)
- Instrucciones Cloud Agent: [`../../AGENTS.md`](../../AGENTS.md)

## Regla de oro

**Nunca perder una lectura de pesaje en edge.** En código: captura local (SQLite outbox) antes que sync a nube. En proceso: no mergear cambios que rompan ingest idempotente o la outbox sin tests.

## Orden de lectura sugerido

1. [`product-principles.md`](product-principles.md) — cómo se construye aquí
2. [`engineering-rules.md`](engineering-rules.md) — cómo se decide aquí
3. [`workflow.md`](workflow.md) — cómo se trabaja día a día
4. El documento del dominio que toques: [`edge-reliability.md`](edge-reliability.md) (device), [`hardware-boundary.md`](hardware-boundary.md) (drivers / PCB)
5. [`sprints.md`](sprints.md) + [`pull-requests.md`](pull-requests.md) al entregar
6. [`unblock.md`](unblock.md) en cuanto algo se atore
