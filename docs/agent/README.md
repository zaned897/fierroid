# Guías para agentes (Cursor / Cloud Agent)

Documentación de **cómo trabajar en Fierro IoT**: flujo de desarrollo, PRs, Jira, pruebas y convenciones del repo.

Los agentes deben leer esto **antes** de implementar cambios no triviales.

## Índice

| Documento | Contenido |
|-----------|-----------|
| [`workflow.md`](workflow.md) | Principios, flujo diario, qué hacer / qué no hacer |
| [`pull-requests.md`](pull-requests.md) | Ramas, commits, PRs, merge a `main` |
| [`jira.md`](jira.md) | Cuándo abrir tickets, plantillas, duplicados, Atlassian MCP |
| [`testing.md`](testing.md) | Lint, tests, evidencia, mock hardware |

## Skills en el repo

Atajos en `.cursor/skills/` (mismo contenido, formato skill):

| Skill | Uso |
|-------|-----|
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
