# #152 — Barra superior del home

Estado: implementada, con validación visual en navegador pendiente por permisos
del entorno. Sin commit, push ni PR, por instrucción del usuario.

## Diseño aprobado

El dueño aprobó **A, cristal a lo ancho**, el 2026-11-12 en el
[comentario del issue](https://github.com/zaned897/fierroid/issues/152#issuecomment-6843233188),
con enlace al [artefacto de diseño](https://claude.ai/artifact/MdQfLzp4Wn5SkHqx6c3Lzu).
Se reutiliza esa aprobación; no se inventa una segunda decisión ni se marca
esta implementación como aceptada visualmente. El artefacto no pudo abrirse
desde la herramienta web; la dirección se tomó del comentario explícito del dueño.

## Resultado

- Fondo transparente al inicio; marfil al 94%, blur de 12 px, borde y sombra
  suaves al fijarse. Fondo sólido cuando falta `backdrop-filter`.
- Transiciones de 180 ms; sin transiciones de deslizamiento con movimiento reducido.
- Los mismos seis enlaces, con `scroll-target-group` / `:target-current` y
  `aria-current="location"`. Respaldo mediante `IntersectionObserver`, sin otro
  listener de `scroll`. Subrayado mediante CSS anchor positioning donde existe;
  borde estático donde no existe. Se conserva en colores forzados.
- Login visible; lista de espera como acción sólida. Una sola navegación semántica
  que pasa a Popover por debajo de 1200 px para que quepan los seis destinos y
  las acciones. En navegadores sin Popover se usa `dialog.showModal()`.
- El menú usa cierre nativo con Esc; elegir un enlace cierra el menú y lleva el
  foco a su sección. Cambiar de ancho no deja el foco dentro de un panel oculto.
- Se conserva el hook de ocultación y se cancela su frame al desmontar.
  La barra se revela al recibir foco y permanece visible con el menú abierto.
  Al restaurar una página desplazada se inicializa como fija y visible.

No se cambian marca, destinos, API, datos, autenticación ni dependencias.

## Comprobaciones ejecutadas (2026-11-17)

| Comprobación | Resultado |
|---|---|
| Instalación web con pnpm 10 y lockfile congelado | Correcta, lockfile sin cambios |
| `pnpm lint` | Correcto |
| `pnpm test` | 28 correctas |
| `pnpm build` | Correcto |
| `ruff check apps scripts` | Correcto |
| `mypy apps/api/src apps/device-agent/src scripts` | Correcto, 36 archivos |
| `diff -r .cursor/skills .claude/skills` | Sin diferencias |
| `FIERRO_MOCK_HW=1 pytest apps/device-agent apps/api tools/agentes -q` | 193 correctas; 101 omitidas por falta de PostgreSQL/DSN |
| Harness temporal React + JSDOM | Aserciones correctas; no sustituye a un navegador |

Se usó `npx pnpm@10` porque no hay ejecutable global de pnpm. Python se ejecutó
con el entorno disponible en `/tmp/astra154-python` y `PYTHONPATH` apuntando a
`apps/api/src:apps/device-agent/src` de este checkout. Los jobs completos de
PostgreSQL y Docker Compose de CI no se pudieron validar localmente; `docker info`
no respondió y se interrumpió. No se afirma que CI haya corrido remotamente.

El harness temporal `/tmp/fierro-152-check/behavior.mjs` comprueba los seis
destinos, scrollspy de respaldo en ambas direcciones, invocación/cierre del
dialog de respaldo, foco en el destino, foco al cambiar de ancho y limpieza
de efectos. También monta el Home real y verifica scroll restaurado, ocultación
al bajar, reaparición al subir, protección del foco y vuelta al inicio.
Comprueba además que la franja de observación conserva 1 px al cambiar a una
pantalla baja: `rootMargin` usa píxeles porque sus porcentajes se resuelven
contra el ancho, según la [especificación de Intersection Observer](https://www.w3.org/TR/intersection-observer/#dom-intersectionobserver-rootmargin).
Las APIs de geometría y dialog están simuladas: no acredita comportamiento
nativo de Esc, pintura CSS ni accesibilidad completa.

### Modern Web Guidance aplicada

- `navbar`: mantuve una sola navegación y el cierre nativo («Do not add document-level click-outside, Escape or focus-restoration handlers»).
- `scrollspy`: reflejé el estado visual en `aria-current` y añadí el respaldo del observador («the visual state must be mirrored with aria-current»).
- `anchor-positioning-tab-underline`: dibujé el indicador con borde, también visible en colores forzados («Draw the underline with a border»).

### Contraste calculado

Ratios calculados con luminancia relativa sRGB y composición alfa. Para el
cristal se usa negro puro debajo, el peor fondo para este texto oscuro.

| Combinación | Ratio |
|---|---:|
| Texto `#102b22` sobre marfil `#f7f8f3` al inicio | 14.15:1 |
| Texto sobre marfil al 94% encima de negro | 12.39:1 |
| Petróleo `#176575` sobre ese mismo cristal | 5.46:1 |
| Blanco sobre botón petróleo | 6.66:1 |

Todas superan 4.5:1 para texto normal. La portada permanece debajo de la barra
en el flujo; cuando la foto u otras secciones pasan detrás, ya aplica el cristal.
Falta confirmar la composición final mediante capturas.

## Pendientes y bloqueo visual

1. Playwright con Chrome local: el proceso terminó con `SIGABRT` / `EPERM`.
2. Computer Use: Chrome no disponible; inventario sin navegadores conectados.
3. Firefox mediante Computer Use: acceso rechazado por falta de autorización.

Causa: el entorno no permite un navegador para validar la interfaz. Se aplicó
[fierro-unblock](../../../.claude/skills/fierro-unblock/SKILL.md):
«Change strategy or deliver an alternative». La alternativa fue validar lógica
y CI local; no generar capturas falsas ni repetir el mismo lanzamiento.

| Opción | Costo | Riesgo | Reversible |
|---|---|---|---|
| Revisar con navegador autorizado antes de abrir PR (recomendada) | Bajo | Permite detectar fallos visuales pendientes | Sí |
| Abrir PR sin capturas | Bajo | Incumple la evidencia exigida | Sí |

Antes de considerar completo el issue:

- [ ] Revisar 375, 390, 768 y 1440 px: sin desbordamiento y acciones alcanzables.
- [ ] Capturas **375 arriba**, **375 fija**, **1440 arriba**, **1440 fija**.
- [ ] Teclado real: Tab/Shift+Tab, Esc devuelve foco al invocador, click fuera,
  enlaces, cambio de ancho con menú abierto e inicio de sesión.
- [ ] Verificar el subrayado CSS y el respaldo en navegadores reales, movimiento
  reducido y colores forzados.
- [ ] Medir CLS: el encabezado conserva altura/borde en ambos estados y el menú
  usa la capa superior, pero no se ha realizado una medición en navegador.

## Entrega y texto para el PR

La asignación a `zaned897` fue rechazada por la herramienta GitHub porque la
política de aprobación es `never`. Crear `agente/barra-superior` también falló:
`.git` es de solo lectura. Los cambios permanecen sin commit en
`exp/codex-astra-152`, checkout inicial en `b80ad248`. No se reabrió el issue,
que GitHub ya marcaba cerrado. No se creó un PR sin commits.

Título sugerido: **Moderniza la barra del home con cristal, sección activa y menú móvil**.

> La barra muestra cristal marfil al fijarse, indica la sección activa y conserva
> el acceso a sesión. Los seis enlaces se muestran en un menú nativo en pantallas
> estrechas. Implementa la variante A aprobada, con respaldos para CSS moderno,
> Popover y movimiento reducido. Closes #152.

Adjuntar esta revisión, el enlace de aprobación y las cuatro capturas al PR;
completar las casillas pendientes antes de solicitar revisión final.
Es un cambio de frontend público: no toca captura, persistencia ni sincronización;
un apagón o 5000 devices no introduce ninguna operación nueva en edge/API.
