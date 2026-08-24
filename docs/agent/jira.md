# Jira — tickets y trazabilidad

Cómo usar Jira con el desarrollo de Fierro IoT (agentes y humanos).

## Cuándo crear o usar un ticket

| Situación | Acción |
|-----------|--------|
| Feature acordada (sprint, epic) | Story o Task; enlazar PR |
| Bug reproducible | Bug; buscar duplicados primero |
| Spike / investigación (pesa, LTE, RFID) | Task con criterios de salida |
| Solo doc interna o typo | Opcional: commit directo o Task pequeño |
| Trabajo ya en PR sin ticket | Crear ticket retroactivo o enlazar epic existente |

## Antes de crear un ticket duplicado

1. Buscar issues similares por resumen, error o componente.
2. Si existe: comentar en el ticket con nuevo contexto o enlazar PR.
3. Si no existe: crear con plantilla abajo.

En Cursor, si **Atlassian MCP** está autenticado, usar herramientas del namespace `Atlassian` (JQL, crear issue, comentar). Si no hay MCP, documentar en el PR y pedir al usuario crear el ticket manualmente.

Skill útil del ecosistema Cursor: **triage-issue** (buscar duplicados y estructurar bugs).

## Tipos de issue (recomendado)

| Tipo | Uso en Fierro |
|------|----------------|
| **Epic** | Sprint theme (ej. "Prototipo físico báscula + RFID") |
| **Story** | Valor de usuario (ej. "Ver historial de peso por arete en PWA") |
| **Task** | Trabajo técnico (driver RS232, migración Postgres) |
| **Bug** | Comportamiento incorrecto con pasos de repro |

## Plantilla — Story / Task

**Summary:** `[componente] Verbo + resultado`  
Ej.: `[device-agent] Leer peso estable desde indicador RS232`

**Description:**

```markdown
## Contexto
Por qué hace falta (enlace a docs/architecture.md o README si aplica).

## Alcance
- [ ] Item 1
- [ ] Item 2

## Fuera de alcance
- ...

## Criterios de aceptación
- [ ] Criterio medible 1
- [ ] Tests / evidencia definida

## Notas técnicas
- Apps: device-agent | api | web
- Riesgos: edge / LTE / hardware
```

**Labels sugeridos:** `fierro`, `edge`, `api`, `web`, `hardware`, `infra`

**Component / custom fields:** según proyecto Jira del equipo (configurar una vez en el board).

## Plantilla — Bug

**Summary:** `[bug] Síntoma breve`

**Description:**

```markdown
## Pasos para reproducir
1.
2.

## Resultado actual

## Resultado esperado

## Entorno
- device_id / versión agent / API / mock vs hardware

## Logs / evidencia

## Severidad propuesta
Blocker | Critical | Major | Minor
```

## Vincular PR y Jira

En commit o PR body:

```
FIERRO-42
```

o

```
Jira: https://<tenant>.atlassian.net/browse/FIERRO-42
```

Al mergear: mover ticket a **Done** (o estado del workflow del equipo) y opcionalmente pegar enlace al PR.

## Flujo del agente con Jira

```
1. Usuario pide feature/bug
2. ¿Hay ticket? → Si no, buscar duplicados → crear o comentar
3. Implementar en rama cursor/*-7dff
4. PR → main con "FIERRO-XX" en descripción
5. Tras merge, actualizar ticket (si MCP disponible)
```

## Proyecto / claves

> **Configuración pendiente del equipo:** reemplazar `FIERRO` por la clave real del proyecto Jira (ej. `FIERR`, `GAN`, etc.).

Hasta tener proyecto fijo:

- Usar placeholder `FIERRO-XXX` en docs de PR.
- En [`README.md`](../../README.md) decisiones abiertas, anotar clave Jira cuando exista.

## Atlassian MCP (Cursor)

Si el namespace `Atlassian` aparece en herramientas dinámicas y `namespaceStatus` es `ready`:

1. `GetDynamicTools` → namespace `Atlassian` para ver schemas.
2. Buscar issues con JQL (proyecto + texto).
3. Crear issue con tipo, summary, description, project key.
4. Comentar o transicionar estado según herramientas disponibles.

Si `needsAuth`: el usuario debe autenticar Atlassian en Cursor IDE; el agente no puede crear tickets hasta entonces.

## Escalación

Pedir al usuario si falta:

- Clave de proyecto Jira
- Epic padre para el sprint
- Permisos para crear issues en el board
- Definición de severidad / workflow (QA → Done)
