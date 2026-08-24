# Protocolo de desbloqueo

Qué hacer cuando el desarrollo **se estanca**: un driver que no responde, una dependencia rota,
un hardware que no llegó, un bug que no se reproduce, un enfoque que no converge.

> **Regla central:** insistir en silencio es el peor resultado posible.
> Un agente atascado debe cambiar de estrategia o entregar una alternativa, nunca seguir intentando lo mismo.

---

## 1. Detectar el estancamiento (timebox)

Se declara estancamiento cuando ocurre **cualquiera** de estas:

| Señal | Umbral |
|---|---|
| Mismo error tras varios intentos distintos | **3 intentos** |
| Tiempo en un solo sub-problema sin avance medible | **~45 min** |
| Se necesita algo que no está disponible | Inmediato (hardware, credencial, manual, decisión) |
| La solución requiere cambiar un contrato o infra no acordada | Inmediato |
| Los tests "pasan" solo desactivando o falseando algo | Inmediato |

Al cruzar el umbral: **parar y aplicar la escalera de abajo.** No hay intento número 4 del mismo enfoque.

## 2. La escalera de alternativas

En orden. Bajar un escalón solo si el anterior no aplica.

### Escalón 1 — Reducir el alcance a un vertical slice

Entregar la versión más delgada que funciona de punta a punta y ticketear el resto.
*Ejemplo: el indicador tiene 6 modos de trama → soportar el modo estable documentado, ticket para los demás.*

### Escalón 2 — Stub detrás de la interfaz

Si el bloqueo está de un lado de una frontera (HAL, transporte, persistencia), implementar el otro lado contra la interfaz y dejar el stub que **falla ruidosamente**.

- ✅ `raise NotImplementedError("protocolo del indicador X pendiente")` — patrón ya usado en `SerialHardware`
- ❌ Devolver un peso inventado, `pass` silencioso, o `except: pass`

Un stub siempre lleva ticket enlazado en el comentario.

### Escalón 3 — Camino alternativo

Cambiar de enfoque, no de intensidad. Alternativas típicas en este proyecto:

| Bloqueo | Alternativa |
|---|---|
| Protocolo del indicador desconocido | Capturar tráfico crudo del puerto y trabajar sobre bytes reales |
| No hay báscula física | Simulador serial (`socat`/pty) + fixtures de captura |
| LTE / Sixfab no disponible | Desarrollar sobre Wi-Fi; el transporte está detrás de interfaz |
| Librería que no compila en ARM | Buscar equivalente en stdlib antes de pelear con el build |
| MQTT no configurable aún | HTTP batch ya funciona; MQTT es evolución, no requisito |
| Postgres no aprovisionado | SQLite de API sigue siendo válido para MVP |
| Bug no reproducible | Añadir observabilidad y cerrar el intento; ticket con lo aprendido |

### Escalón 4 — Spike con timebox

Si nada es evidente, convertirlo en **ticket tipo Spike** con:

- Pregunta concreta a responder
- Timebox explícito (p. ej. 4 h)
- Criterio de salida: una recomendación escrita, no código de producción

### Escalón 5 — Escalar al usuario

Cuando se necesita una **decisión** o un **recurso** que el agente no puede obtener.
Ver formato en §4. **No** quedarse esperando: entregar primero todo lo que no dependía de esa respuesta.

## 3. Qué está prohibido al estar atascado

- ❌ **Datos falsos silenciosos.** Nunca simular una lectura para "que pase el test".
- ❌ **`try/except` vacío** para tapar el síntoma.
- ❌ **Desactivar o borrar tests** que estorban.
- ❌ **Reescribir medio repo** porque el enfoque original no salió. Diff mínimo sigue vigente.
- ❌ **Cambiar el contrato de datos** sin ticket ni migración.
- ❌ **Reportar como terminado** algo que quedó a medias. Se dice qué quedó fuera y por qué.
- ❌ **Insistir con el mismo comando fallando** en bucle.

## 4. Formato para escalar

Cuando se escala, el mensaje incluye **siempre** estas cinco partes:

```markdown
## Bloqueo
Qué se intentaba lograr y dónde se detuvo.

## Intentado
1. Enfoque A → resultado
2. Enfoque B → resultado
3. Enfoque C → resultado

## Causa raíz (o hipótesis)
Qué falta realmente: dato, hardware, decisión o acceso.

## Opciones
| Opción | Costo | Riesgo | Reversible |
|---|---|---|---|
| A | ... | ... | sí/no |
| B | ... | ... | sí/no |

## Recomendación
Una opción, con su razón. No una lista sin postura.

## Entregado mientras tanto
Lo que sí quedó funcionando y probado, aunque el bloqueo siga.
```

## 5. Decisiones que siempre se escalan

Nunca resolverlas por cuenta propia (son puertas de una sola vía):

- Marca/modelo de báscula, indicador o lector RFID
- País, carrier LTE y bandas
- Cambio del contrato en [`../data-contract.md`](../data-contract.md)
- Migrar a Postgres, MQTT o añadir infra nueva
- Esquema de identidad/credenciales de la flota
- Fabricar una revisión de PCB
- Multi-tenant vs rancho único

## 6. Cerrar el bloqueo

Un estancamiento resuelto **deja rastro**, o se repite:

1. Ticket actualizado con lo aprendido (aunque la conclusión sea "no se puede aún").
2. Si reveló una regla nueva, actualizar el documento correspondiente en `docs/agent/`.
3. Si dejó un stub, el ticket enlazado queda abierto y visible en el sprint.

## Relacionados

- [`engineering-rules.md`](engineering-rules.md) — pragmatismo y decisiones reversibles
- [`sprints.md`](sprints.md) — Spikes y planificación
- [`jira.md`](jira.md) — plantillas de ticket
