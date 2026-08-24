# Pull requests

Convenciones para ramas, commits y PRs en **fierroid**.

## Rama base

- **Base:** `main`
- **Feature branches:** prefijo `cursor/` + nombre descriptivo en kebab-case + sufijo `-7dff`

Ejemplos:

- `cursor/scale-rs232-driver-7dff`
- `cursor/api-postgres-migration-7dff`
- `cursor/pwa-animal-history-7dff`

```bash
git checkout main
git pull origin main
git checkout -b cursor/mi-feature-7dff
```

## Commits

- Mensajes en **inglés o español**, en oraciones completas (imperativo o descriptivo).
- Un commit por cambio lógico; no mezclar fixes no relacionados.
- No incluir secretos, `.env`, credenciales, dumps de DB de producción.

Ejemplos:

```
Add RS232 scale driver skeleton for Gallagher indicator
Fix idempotent ingest when batch body is empty
Expand agent docs for Jira workflow
```

## Antes del PR

1. `./scripts/install-deps.sh` (si cambiaron deps).
2. Lint y tests (ver [`testing.md`](testing.md)).
3. Push:

```bash
git push -u origin cursor/mi-feature-7dff
```

## Crear el PR

- **Destino:** `main`
- **Estado inicial:** draft (salvo que el usuario pida review directo).
- **Título:** qué hace el cambio, no cómo (ej. "Add device heartbeat fields to PWA").

### Cuerpo sugerido

```markdown
## Summary
- Bullet 1: qué cambió y por qué
- Bullet 2: impacto (edge / API / web)

## Test plan
- [ ] ruff check apps
- [ ] pytest apps/device-agent apps/api
- [ ] pnpm lint / build (si web)
- [ ] Manual: mock agent → API → PWA (si aplica)

## Jira
- FIERRO-123 (opcional: enlace o "N/A")
```

### Evidencia

Para cambios de UI o flujo end-to-end, incluir screenshot o video en el cuerpo del PR cuando exista.

## Durante el review

- Responder comentarios con commits nuevos en la misma rama (no force push salvo pedido).
- Actualizar descripción del PR si el alcance cambia.
- Marcar PR **ready for review** solo cuando lint/tests pasen y el checklist esté completo.

## Merge

- **No** auto-merge ni `gh pr merge` salvo instrucción explícita del usuario.
- Tras merge a `main`, sincronizar Jira (Done / enlace al PR).

## Push directo a `main`

Solo cuando el usuario lo pida explícitamente (docs menores, hotfix acordado):

```bash
git checkout main
git pull origin main
# ... commits ...
git push origin main
```

Preferir PR para cambios de código de producto.

## Checklist rápido del agente

- [ ] Rama `cursor/*-7dff` creada desde `main` actualizado
- [ ] Tests ejecutados (no solo "debería compilar")
- [ ] Sin archivos generados accidentales en el diff
- [ ] PR creado/actualizado hacia `main`
- [ ] Ticket Jira enlazado o creado si aplica
