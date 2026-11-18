# Barra superior — issue #152

Diseño: [variante A, cristal a lo ancho](https://claude.ai/artifact/MdQfLzp4Wn5SkHqx6c3Lzu).
[Aprobación del dueño, 2026-11-12](https://github.com/zaned897/fierroid/issues/152#issuecomment-6843233188).
La aprobación ya existía antes de esta implementación; no se propone una variante nueva.

## Implementación

- Fondo transparente en la portada. Al desplazarse, marfil al 94%, desenfoque
  de 12 px, borde fino y sombra al 5%. Sin `backdrop-filter`, fondo opaco.
- Transiciones de 180 ms. Movimiento reducido elimina el deslizamiento de la
  barra y del indicador. Se conservan la altura y el borde reservado en ambos
  estados; el menú se abre en la capa superior, fuera del flujo.
- Los seis destinos conservan sus anclas. `IntersectionObserver` actualiza
  `aria-current="location"` en las dos navegaciones, sin añadir listeners de
  scroll. El subrayado usa CSS anchor positioning; sin soporte queda un borde.
  El observador se recalcula al cambiar el alto de la ventana.
- Iniciar sesión sigue usando `onEntrar`, como acción de texto siempre visible.
  Unirme a la lista es la píldora sólida. Los nuevos controles tienen un
  diccionario traducible y objetivos de al menos 44 px de alto.
- Bajo 1200 px se usa Menú para que quepan los seis destinos y las dos acciones.
  Popover API controla apertura, Esc y cierre al pulsar fuera. Sin Popover se
  usa un `<dialog>` modal nativo. Cerrar y elegir enlace devuelven el foco al
  disparador. Al pasar a escritorio se cierra y se enfoca el login visible.
- La barra conserva su único listener de scroll, no se oculta con foco dentro
  ni con el menú abierto y cancela el frame pendiente al desmontar.

## Verificaciones ejecutadas — 2026-11-17

| Comprobación | Resultado |
|---|---|
| `pnpm install --frozen-lockfile` | Correcto; sin cambios de dependencias ni lockfile |
| `pnpm lint` | Correcto |
| `pnpm test` | 28 aprobadas |
| `pnpm build` | Correcto |
| `ruff check apps scripts` | Correcto |
| `mypy apps/api/src apps/device-agent/src scripts` | Correcto, 36 archivos |
| `diff -r .cursor/skills .claude/skills` | Sin diferencias |
| `FIERRO_MOCK_HW=1 pytest apps/device-agent apps/api tools/agentes -q` | 193 aprobadas, 101 omitidas por PostgreSQL/DSN ausente |
| Integración DOM con React StrictMode y jsdom | Correcta para las rutas Popover y dialog, con APIs nativas simuladas |

La integración DOM comprobó los seis estados activos al avanzar y retroceder,
el estado sin sección sobre la portada, los destinos reales, login, cierre y
devolución de foco, ocultación al bajar, reaparición al subir, permanencia con
foco dentro, reconstrucción al redimensionar y limpieza de efectos.
Se ejecutó con un script temporal y herramientas fuera del repo; no forma
parte de `pnpm test` ni prueba el comportamiento nativo de Esc o el layout.

Contraste calculado con luminancia relativa sRGB:

| Combinación | Relación |
|---|---|
| Texto `#102b22` / marfil | 14.15:1 |
| Texto / marfil 94% compuesto sobre negro (peor caso fotográfico) | 12.39:1 |
| Marca `#143c2d` / mismo peor caso | 10.05:1 |
| Blanco / petróleo `#176575` | 6.66:1 |
| Hover petróleo / niebla `#edf5ef` | 5.99:1 |

La transparencia total inicial está sobre el fondo marfil de la página: la
cabecera mantiene su espacio antes de la portada y su fotografía. El cálculo
no sustituye la revisión visual sobre la fotografía real.

## Pendiente de verificación en navegador

- Capturas a 375 y 1440 px, tanto arriba como fija; además revisar 390 y 768 px.
- Abrir con teclado, recorrer los enlaces, cerrar con Esc y comprobar foco,
  cierre exterior y el respaldo dialog en un navegador real.
- Comprobar el subrayado con/sin anchor positioning y movimiento reducido.
- Medir CLS y comprobar ausencia de desbordamiento y regresiones visuales.
- Ejecutar el job Compose y las pruebas contra PostgreSQL de CI.

Chrome headless terminó con `SIGABRT` en este entorno. No hay navegador web
conectado en Computer Use; el acceso a Firefox fue rechazado. Por ello no se
adjuntan capturas ni se afirma una validación visual o una medición de CLS.

## Entrega

Texto de cierre para el futuro PR: `Closes #152`. Incluir los enlaces de diseño
y aprobación de arriba y las capturas pendientes. No se hizo commit ni PR.
El entorno no permite escribir en `.git`: no se pudo crear
`agente/barra-superior`; los cambios quedan en `exp/codex-sol-152`.
La asignación a `zaned897` fue rechazada por la política de aprobación del
conector. El issue remoto ya figuraba cerrado al iniciar la tarea y no se
modificó su estado.
