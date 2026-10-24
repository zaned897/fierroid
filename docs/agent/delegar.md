# Delegar a Codex y Antigravity

Claude Code es el dueño de la tarea y del PR. Codex (OpenAI) y Antigravity (`agy`, Google)
ayudan con piezas acotadas; lo que devuelven es un diff que Claude revisa, prueba y decide
si integrar. Herramienta: [`scripts/delegar.py`](../../scripts/delegar.py).

## Dónde funciona

Las CLIs y sus sesiones (`codex login`, cuenta de Antigravity) viven en la PC del usuario.
La delegación funciona cuando Claude Code corre ahí, directo o por Remote Control. En la
nube no hay CLIs: el script sale con código 2 y lo dice, y el hook no hace nada.

## Qué va a quién

| Agente | Le toca | No le toca |
|--------|---------|------------|
| **Codex** | Tareas de Python/API con criterio de éxito claro: pruebas que faltan, un endpoint con contrato ya definido, un refactor mecánico, scripts. Segunda opinión sobre el diff (`review` y el hook) | Outbox, sync, idempotencia, drivers |
| **Antigravity** | UI en `apps/web` desde una pantalla ya aprobada, ajustes visuales, verificación en navegador, leer documentos largos (manuales de indicadores, datasheets) y resumirlos | Contratos de datos, lógica del device agent |
| **Claude** | Diseño y decisiones, `apps/device-agent` (outbox SQLite, sync, energía), idempotencia por `event_id`, frontera de hardware, integrar y abrir PRs | — |

Regla para decidir: delega cuando la tarea cabe en un párrafo, tiene una forma objetiva de
saber si quedó (una prueba, una captura) y no toca el invariante raíz. Si dudas, no delegues.

## Uso

```bash
python scripts/delegar.py codex "agrega pruebas para ingest con lote vacío en apps/api"
python scripts/delegar.py agy "aplica el espaciado de la pantalla aprobada a AnimalCard"
python scripts/delegar.py agy --modo plan "lee docs/x.pdf y resume el protocolo serial"
python scripts/delegar.py review   # segunda opinión de Codex sobre el diff contra main
```

Cada tarea crea un worktree en `.claude/worktrees/delegar-<agente>-<slug>-<fecha>` con la
rama `delegar/...`, partiendo de `HEAD` (`--base` para otro commit). El agente no hace commit.
El resumen del agente queda en `.claude/delegaciones/`. Ambas rutas están en `.gitignore`.

Después de delegar, Claude:

1. Lee el resumen y `git -C <worktree> diff HEAD`. Lo trata como código de otro: verifica, no confía.
   El script marca los archivos nuevos con `git add -N`, así que el diff los incluye.
2. Corre lint y pruebas en el worktree (`ruff`, `pytest`, `pnpm lint && pnpm build`).
3. Trae lo que sirve a su rama (`git -C <worktree> diff HEAD --binary | git apply`) y descarta el resto.
4. Limpia: `git worktree remove --force <worktree>` y `git branch -D delegar/...`.

Códigos de salida: `0` terminó, `2` falta la CLI, `3` se pasó del límite de tiempo,
`4` agy no trabajó porque el modo headless le negó un permiso.

Codex corre con `--sandbox workspace-write` dentro del worktree.

### Permisos de agy

`agy -p` no puede preguntar permisos: niega en automático cualquier herramienta que no esté
permitida y sale con código 0 sin hacer nada (el script lo detecta y devuelve `4`). Antes de
delegarle algo que necesite correr comandos, el usuario agrega reglas `command(<comando>)` en
`permissions.allow` del `settings.json` de Antigravity, solo para lo que la tarea necesita
(por ejemplo `git`, `pnpm`, `python`). El script no pasa `--dangerously-skip-permissions`.
`--mode auto` no existe en Windows (agy no tiene sandbox de terminal ahí) y cae al modo normal.

## Hook de revisión de Codex

`.claude/settings.json` registra un hook `Stop` que, con `FIERRO_CODEX_REVIEW=1`, le pide a
Codex revisar el diff contra `main` cuando Claude termina un turno. Revisa cada estado del diff
una sola vez y no encadena revisiones. Si Codex reporta algo, Claude lo recibe y lo verifica
antes de actuar. Sin la variable, o sin `codex` en el PATH, el hook no hace nada.

Para prenderlo en tu PC, en `.claude/settings.local.json` (no se versiona):

```json
{ "env": { "FIERRO_CODEX_REVIEW": "1" } }
```
