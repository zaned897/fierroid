# Delegar a Codex y Antigravity

Claude Code es el dueño de la tarea y del PR. Codex (OpenAI) y Antigravity (`agy`, Google)
ayudan con piezas acotadas; lo que devuelven es un diff que Claude revisa, prueba y decide
si integrar. Herramienta: [`tools/agentes/delegar.py`](../../tools/agentes/delegar.py); el contexto que recibe el otro
agente está en `tools/agentes/preambulo.md` y lo que cuenta en una revisión en `tools/agentes/revision.md`.

## Dónde funciona

Las CLIs y sus sesiones (`codex login`, cuenta de Antigravity) viven en la PC del usuario.
La delegación funciona cuando Claude Code corre ahí, directo o por Remote Control. En la
nube no hay CLIs: el script sale con código 2 y lo dice, y el hook no hace nada.

## Qué va a quién

| Agente | Le toca | No le toca |
|--------|---------|------------|
| **Codex** | Tareas de Python/API con criterio de éxito claro: pruebas que faltan, un endpoint con contrato ya definido, un refactor mecánico, scripts. Segunda opinión sobre el diff (`review` y el hook) | Outbox, sync, idempotencia, drivers |
| **Antigravity** | Ediciones de UI en `apps/web` desde una pantalla ya aprobada, ajustes visuales, leer documentos largos (manuales de indicadores, datasheets) y resumirlos. Solo edita, no corre comandos | Contratos de datos, lógica del device agent, tareas que necesiten correr pruebas |
| **Claude** | Diseño y decisiones, `apps/device-agent` (outbox SQLite, sync, energía), idempotencia por `event_id`, frontera de hardware, integrar y abrir PRs | — |

Regla para decidir: delega cuando la tarea cabe en un párrafo, tiene una forma objetiva de
saber si quedó (una prueba, una captura) y no toca el invariante raíz. Si dudas, no delegues.

## Uso

```bash
python tools/agentes/delegar.py codex "agrega pruebas para ingest con lote vacío en apps/api"
python tools/agentes/delegar.py agy "aplica el espaciado de la pantalla aprobada a AnimalCard"
python tools/agentes/delegar.py agy --modo plan "lee docs/x.pdf y resume el protocolo serial"
python tools/agentes/delegar.py review   # segunda opinión de Codex sobre el diff contra main
python tools/agentes/delegar.py estado   # qué CLIs hay en esta máquina
python tools/agentes/delegar.py limpiar  # quita worktrees y ramas delegar/*
```

Cada tarea crea un worktree en `.claude/worktrees/delegar-<agente>-<slug>-<fecha>` con la
rama `delegar/...`, partiendo de `HEAD` (`--base` para otro commit). El agente no hace commit.
El resumen del agente queda en `.claude/delegaciones/`. Ambas rutas están en `.gitignore`.

Después de delegar, Claude:

1. Lee el resumen y `git -C <worktree> diff HEAD`. Lo trata como código de otro: verifica, no confía.
   El script marca los archivos nuevos con `git add -N`, así que el diff los incluye.
2. Corre lint y pruebas en el worktree (`ruff`, `pytest`, `pnpm lint && pnpm build`).
3. Trae lo que sirve a su rama (`git -C <worktree> diff HEAD --binary | git apply`) y descarta el resto.
4. Limpia: `python tools/agentes/delegar.py limpiar`.

Códigos de salida: `0` terminó, `2` falta la CLI, `3` se pasó del límite de tiempo,
`4` agy no trabajó porque el modo headless le negó un permiso.

Codex corre con `--sandbox workspace-write` dentro del worktree.

### agy solo edita

`agy -p` lee y edita archivos, pero no corre comandos. Su modo de permisos por defecto
(`toolPermission: request-review`) pide confirmar cada comando aunque esté en
`permissions.allow`, y sin terminal esa confirmación se niega sola. Por eso el script le
pide no correr comandos, y Claude corre lint y pruebas al revisar el diff. Si agy intenta un
comando igual, sale con código 0 sin hacer nada; el script lo detecta y devuelve `4`.

Para que corra comandos habría que aprobarle todo (`toolPermission: always-proceed` o
`--dangerously-skip-permissions`). El script no lo hace: lo que necesite comandos va a Codex.

## Hook de revisión de Codex

`.claude/settings.json` registra un hook `Stop` que, con `CODEX_REVIEW=1`, le pide a
Codex revisar el diff contra `main` cuando Claude termina un turno. Revisa cada estado del diff
una sola vez y no encadena revisiones. Si Codex reporta algo, Claude lo recibe y lo verifica
antes de actuar. Sin la variable, o sin `codex` en el PATH, el hook no hace nada.

Para prenderlo en tu PC, en `.claude/settings.local.json` (no se versiona):

```json
{ "env": { "CODEX_REVIEW": "1" } }
```
