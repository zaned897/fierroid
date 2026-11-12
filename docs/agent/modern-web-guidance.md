# Modern Web Guidance

[Modern Web Guidance](https://developer.chrome.com/docs/modern-web-guidance) es una
skill externa (Chrome, Edge, Firefox y MDN; Apache-2.0) que trae al contexto del agente
guías actualizadas de HTML, CSS y JS de cliente: `<dialog>`, Popover API, anchor
positioning, container queries, scroll-driven animations, view transitions, formularios,
accesibilidad y Core Web Vitals (LCP, INP, CLS), con compatibilidad Baseline.

Los modelos tienden a escribir patrones viejos (JS a mano para menús, modales y
animaciones de scroll). Esta skill los empuja a la solución nativa, más ligera y
accesible, que es lo que pide `fierro-product-principles` (elegancia, mínimo).

## Cuándo

Antes de escribir o cambiar HTML, CSS o JS de cliente en `apps/web`. No aplica a
`apps/api`, `apps/device-agent`, scripts, CI ni configuración de Vite.

## Instalación por agente

No se copia al repo: se instala desde su origen para recibir actualizaciones.

| Agente | Cómo |
|--------|------|
| Claude Code | Automático: `.claude/settings.json` declara el marketplace `googlechrome` y activa `modern-web-guidance@googlechrome`. Al abrir el repo, aceptar la confianza del marketplace. A mano: `claude plugin marketplace add GoogleChrome/modern-web-guidance` y `claude plugin install modern-web-guidance@googlechrome` |
| Cursor, Codex u otros | `npx modern-web-guidance@latest install` (asistente interactivo) o `npx skills add GoogleChrome/modern-web-guidance` |
| Antigravity | `agy plugin install https://github.com/GoogleChrome/modern-web-guidance` |

## Uso sin instalar

```bash
npx -y modern-web-guidance@latest search "light dismiss dialog"
npx -y modern-web-guidance@latest retrieve "<id>"
npx -y modern-web-guidance@latest legacy-scan apps/web   # patrones viejos a modernizar
```

## Reglas de Fierro que siguen mandando

- La guía propone; `docs/frontend-home.md` y la especificación aprobada deciden qué se construye.
- Respetar `prefers-reduced-motion` y no subir el tamaño del build sin justificarlo.
- Una API sin soporte Baseline amplio necesita respaldo que no rompa la página.
