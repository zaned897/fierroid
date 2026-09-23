---
name: fierro-frontend-self-driven
description: "Implementa interfaces de Fierro por ciclos pequeños, verificables y reanudables. Usar al construir o continuar una pantalla desde una especificación versionada; no usar para API, hardware ni rediseños sin especificación aprobada."
---

# Fierro frontend self-driven

Guía completa:
[`docs/agent/frontend-self-driven.md`](../../../docs/agent/frontend-self-driven.md).

## Resultado

Entregar una sola unidad funcional por ciclo, con diff mínimo, validación real y
un relevo escrito. No intentar terminar toda la pantalla en una ejecución.

## Antes de editar

1. Leer `AGENTS.md`, la especificación y la guía completa.
2. Leer `docs/frontend-home-progress.md` si existe.
3. Consultar el grafo para encontrar componentes y dependencias existentes.
4. Revisar `git status` y preservar archivos ajenos.
5. Elegir una unidad con máximo tres resultados verificables.

Para el home, `docs/frontend-home.md` manda sobre los mockups. Estos solo
orientan composición y jerarquía; no autorizan controles, textos ni funciones.

## Durante el ciclo

- Cambiar solo la unidad elegida.
- Reutilizar marca, flujos, componentes y recursos existentes cuando encajen.
- Acotar estilos para no modificar login, dashboard o administración.
- No inventar datos, capacidades, rutas ni promesas.
- No comenzar otra unidad mientras la actual esté roja o incompleta.

## Cierre

- Al tocar código, ejecutar `pnpm lint` y `pnpm build` desde `apps/web`.
- Revisar los criterios y anchos afectados.
- Registrar evidencia, limitaciones y siguiente unidad en
  `docs/frontend-home-progress.md`.
