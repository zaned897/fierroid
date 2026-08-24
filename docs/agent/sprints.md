# Sprints y tickets

Cómo se organiza el trabajo en Fierro IoT. Complementa [`jira.md`](jira.md)
(plantillas y mecánica de Jira); esto define **cadencia, granularidad y criterios**.

> **Regla central:** todo trabajo no trivial nace de un ticket y muere en un PR enlazado.
> Sin ticket no hay contexto; sin PR no hay entrega.

---

## 1. Cadencia

| Elemento | Convención |
|---|---|
| Duración del sprint | **2 semanas** (1 semana es válido en fase de prototipo si el equipo lo prefiere) |
| Objetivo de sprint | **Uno solo**, demostrable. Si no se puede demostrar, no es objetivo |
| Roadmap de sprints | Sección "Sprints iniciales" del [`README`](../../README.md) |
| Backlog vivo | Jira. El README es el rumbo, Jira es el detalle |
| Cierre | Demo del objetivo + actualizar README si el alcance cambió |

**El objetivo del sprint se escribe como resultado observable**, no como lista de tareas:

- ✅ "Una estación real captura pesajes con báscula física y sincroniza por LTE"
- ❌ "Avanzar en drivers y hardware"

## 2. Jerarquía de trabajo

| Nivel | Qué es | Ejemplo |
|---|---|---|
| **Epic** | Tema de sprint o capacidad completa | `Prototipo físico báscula + RFID` |
| **Story** | Valor visible para el usuario | `Ver historial de peso por arete en la PWA` |
| **Task** | Trabajo técnico necesario | `Driver RS232 para indicador Gallagher` |
| **Bug** | Comportamiento incorrecto con repro | `[bug] Duplicados tras reconexión LTE` |
| **Spike** | Investigación con timebox | `Determinar protocolo del indicador X (4 h)` |

**Spike** es de primera clase en este proyecto: mucho del riesgo es hardware desconocido.
Un Spike siempre lleva timebox y criterio de salida. Ver [`unblock.md`](unblock.md).

## 3. Granularidad

1. **Un ticket ≤ 2 días de trabajo.** Si es más, se parte.
2. **Partir en vertical slices, no en capas.** ✅ "capturar y mostrar peso de una báscula" / ❌ "hacer toda la capa de drivers".
3. **Un ticket = una rama = un PR.** Nada de trabajo huérfano fuera de ticket.
4. **Hardware y software nunca en el mismo ticket** (lead time y riesgo distintos). Ver [`hardware-boundary.md`](hardware-boundary.md).
5. **Etiquetas por dominio:** `edge`, `api`, `web`, `hardware`, `pcb`, `infra`, `docs`.
6. **Los tickets de hardware llevan lead time explícito** — fabricar y enviar toma semanas; se planifican un sprint antes.

## 4. Definition of Ready (antes de tomarlo)

Un ticket no se empieza sin:

- [ ] Contexto: por qué existe, enlace a doc si aplica
- [ ] Alcance y **fuera de alcance** explícitos
- [ ] Criterios de aceptación **medibles**
- [ ] Apps afectadas: `device-agent` / `api` / `web` / `hardware`
- [ ] Dependencias identificadas (hardware, credenciales, decisiones abiertas)
- [ ] Riesgo sobre el invariante raíz evaluado ("¿puede perder una lectura?")

Si falta algo → se pregunta al usuario o se convierte en Spike. **No se adivina.**

## 5. Definition of Done (para cerrarlo)

- [ ] Criterios de aceptación cumplidos, uno por uno
- [ ] `ruff check apps` y `pytest apps/device-agent apps/api -q` en verde
- [ ] Web: `pnpm lint && pnpm build` si se tocó `apps/web`
- [ ] Evidencia en el PR (salida de tests, screenshot, curl) — ver [`testing.md`](testing.md)
- [ ] Invariantes de outbox e idempotencia intactos
- [ ] Pruebas de caos relevantes ejecutadas si tocó captura/sync ([`edge-reliability.md`](edge-reliability.md))
- [ ] Docs actualizadas si cambió comportamiento o convención
- [ ] PR enlazado al ticket y ticket movido de estado
- [ ] Stubs pendientes dejaron ticket abierto y visible

**Nunca** marcar Done con tests fallidos, desactivados o "debería funcionar".

## 6. Flujo estándar por ticket

```
Ticket (DoR) → rama cursor/<slug>-7dff → implementar → lint + tests
→ evidencia → PR a main (menciona la clave del ticket) → review → merge → ticket a Done
```

Detalle de ramas y PRs: [`pull-requests.md`](pull-requests.md).

## 7. Reglas del agente en el sprint

1. **Verificar el ticket antes de codear.** Si el usuario pide algo sin ticket: buscar duplicados, y crear o proponer uno.
2. **No ampliar el alcance del ticket sobre la marcha.** Hallazgo fuera de alcance → ticket nuevo, no diff más grande.
3. **No tomar trabajo de sprints futuros** (Postgres, MQTT, OTA) sin que el usuario lo pida: el README ya los ubica más adelante.
4. **Reportar el bloqueo dentro del sprint**, no al final. Ver [`unblock.md`](unblock.md).
5. **Entregar lo que sí se pudo.** Si una parte quedó bloqueada, se completa el resto y se dice explícitamente qué faltó y por qué.
6. **Un hallazgo de riesgo sobre el invariante raíz siempre genera ticket**, aunque no sea del sprint actual.

## 8. Deuda técnica

- Se registra como ticket con etiqueta `deuda`, nunca solo como comentario en el código.
- La lista viva está en "Puntos a mejorar" del [`README`](../../README.md); mantenerla sincronizada.
- Cada sprint reserva capacidad para deuda que afecte confiabilidad. La deuda cosmética espera.

## Relacionados

- [`jira.md`](jira.md) — plantillas y Atlassian MCP
- [`pull-requests.md`](pull-requests.md) — ramas, commits y PRs
- [`unblock.md`](unblock.md) — bloqueos y Spikes
- [`engineering-rules.md`](engineering-rules.md) — cómo decidir
