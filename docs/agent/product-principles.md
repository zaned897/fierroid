# Principios de producto

Cómo se construye Fierro, más allá de las reglas de ingeniería. Cualquier agente
o persona que entre a trabajar debe leer esto **antes** de escribir código.

Estas directivas **no reemplazan** a [`engineering-rules.md`](engineering-rules.md);
la complementan. Donde algo ya esté cubierto ahí, aquí solo se apunta.

---

## 1. Elegancia y pragmatismo antes que estado del arte

> La solución más simple que resuelve el problema real gana. Siempre.

Ya es el pilar 1 de [`engineering-rules.md`](engineering-rules.md); lo que se
agrega aquí es el anti-objetivo explícito:

**No construimos para demostrar sofisticación.** Ni el framework de moda, ni la
arquitectura de la conferencia, ni la abstracción que "algún día servirá". Un
rancho con polvo, sol y LTE intermitente no premia la elegancia técnica: premia
que el número correcto llegue.

| Señal de alarma | Qué hacer |
|---|---|
| "Esto escala mejor si agregamos una capa" | ¿Cuántas estaciones hay hoy? Si son 3, no |
| "Es el estándar de la industria en 2026" | ¿Resuelve un problema que tenemos hoy? |
| Una abstracción con una sola implementación | Bórrala hasta que haya dos |
| Un patrón que nadie del equipo puede explicar en 2 minutos | No entra |

Elegante aquí significa **poco código, obvio de leer, difícil de usar mal**. No
significa ingenioso.

---

## 2. Multi-idioma desde el diseño

Arrancamos en **español**, con **inglés** como segundo idioma, y la estructura
debe permitir un tercero sin reescribir nada.

### Regla de capas

| Capa | Idioma | Por qué |
|------|--------|---------|
| Identificadores de código | inglés | Ya lo es todo el repo; cambiarlo es puro costo |
| Comentarios y docs | español | Es el idioma del equipo |
| **Texto visible al usuario** | **traducible** | Nunca literal en el componente |
| Datos y contrato de eventos | **neutro** | Ver abajo |

### El contrato de datos no tiene idioma

`captured_at` viaja en ISO-8601 UTC. `weight_kg` viaja en kilogramos. El formateo
—`412.5 kg`, `3/9/2026, 6:47 p.m.`— es **presentación**, y vive en el front.

Nunca guardar texto ya formateado ni fechas en formato local. Si la base guarda
`"3/9/2026"` ya perdimos: no sabemos si es 3 de septiembre o 9 de marzo.

### Reglas prácticas

1. **Cero cadenas literales visibles** en componentes. Todas por clave de traducción
2. **No concatenar frases.** `"Hay " + n + " pesajes"` no se traduce a idiomas con
   otra gramática. Usar interpolación con plurales
3. **El idioma se elige, no se adivina.** Detectar del navegador está bien como
   default; sobreescribirlo debe ser posible
4. **Los códigos no se traducen.** `pending`, `synced`, `stable` son valores del
   contrato, no texto. Se traducen al mostrarse
5. **Probar con el idioma más largo.** El alemán rompe layouts que el español aguanta

> Estado actual: [`apps/web`](../../apps/web) tiene el texto literal en español
> dentro de `App.jsx`. Extraerlo es un ticket pendiente, no deuda invisible.

---

## 3. Entrega por etapas: v1, v2, v3

> Cada versión es un **MVP end-to-end**, no una capa terminada.

Una versión se libera cuando un pesaje real recorre el camino completo —arete →
báscula → RPi → nube → PWA— y alguien puede usarlo. Nunca se libera "el backend
de la v2" porque eso no le sirve a nadie en el corral.

### Qué califica como etapa cerrada

- [ ] Recorre el flujo completo, de punta a punta
- [ ] Alguien fuera del equipo puede usarlo sin que le expliquen
- [ ] Tiene pruebas y CI en verde
- [ ] Lo que quedó fuera está escrito y visible

### Versionado

[SemVer 2.0.0](https://semver.org/lang/es/). Un tag `vX.Y.Z` marca una etapa
cerrada y desplegable, no un punto arbitrario del calendario. Ver
[`../environments.md`](../environments.md) para cómo se promueve.

Los sprints son la **cadencia** (ver [`sprints.md`](sprints.md)); las versiones
son el **entregable**. No son lo mismo y no tienen por qué coincidir.

---

## 4. Pruebas, siempre

Cubierto en [`testing.md`](testing.md) y en la Definition of Done de
[`sprints.md`](sprints.md). Lo no negociable, resumido:

- Todo comportamiento nuevo llega con su prueba
- Un bug se cierra con una prueba que **fallaba antes** del arreglo
- Nunca se marca listo con pruebas rojas, saltadas o "debería funcionar"
- Una prueba que solo pasa en condiciones ideales (base vacía, red perfecta,
  reloj sincronizado) **no está probando nada**

---

## 5. Bugs: causa raíz, nunca parches

> Si no sabes **por qué** falla, todavía no puedes arreglarlo.

El orden es fijo:

1. **Reproducir.** Si no se reproduce, no se arregla. Se investiga
2. **Verificar dos veces.** Confirmar la causa por dos caminos distintos: el log
   y el estado de la base; la prueba y el comportamiento real
3. **Escribir una prueba que falle** por esa causa
4. **Arreglar la causa**, no el síntoma
5. **La prueba pasa**, y las demás siguen pasando

### Prohibido

| Antipatrón | Por qué es peor que el bug |
|---|---|
| `try/except` que traga el error | Esconde la falla; el dato malo sigue entrando |
| `if` extra para el caso que falla | Trata el síntoma; la causa sigue viva |
| Reintentar hasta que pase | Convierte un bug determinista en uno intermitente |
| Subir el timeout | Cambia el momento de la falla, no la falla |
| Ajustar la prueba para que pase | Rompe la única señal que teníamos |

Si tras investigar sigues sin certeza, **eso es estar atascado**: aplica
[`unblock.md`](unblock.md). Un stub ruidoso con ticket abierto es honesto; un
parche que "parece arreglarlo" no.

---

## 6. Diseño simple, moderno, minimalista

La PWA se usa **en el corral**: con sol directo, con guantes, con una mano, con
poca señal. Eso define el diseño más que cualquier tendencia.

| Principio | En concreto |
|---|---|
| **Un dato protagonista por pantalla** | El peso es lo grande. Todo lo demás es contexto |
| **Mobile-first, no mobile-también** | Se diseña a 375px y crece, no al revés |
| **Contraste alto** | Se lee con sol. Nada de gris claro sobre blanco |
| **Objetivos táctiles grandes** | Mínimo 44×44px: se usa con guantes |
| **Sin adorno que no informe** | Sin sombras decorativas, sin animación gratuita |
| **Estados vacíos que enseñan** | "Sin pesajes aún" debe decir qué hacer |
| **El error se muestra, no se esconde** | Una lectura inestable se marca, no se oculta |

Menos superficie es mejor: cada control agregado es uno más que explicar,
traducir, probar y mantener.

---

## 7. Compatibilidad de hardware y transporte

El objetivo es que el sistema corra sobre **Raspberry Pi**, con conectividad
**Sixfab / LTE**, y también sobre enlaces **LoRa / LoRaWAN**.

Eso último **no es gratis** y hay que decidirlo con los números a la vista.

### El problema: el evento actual no cabe en LoRaWAN

El evento del [contrato de datos](../data-contract.md) en JSON compacto pesa
**205 bytes**. Los presupuestos de payload de LoRaWAN:

| Banda / Data Rate | Payload máximo | ¿Cabe el evento JSON? |
|---|---|---|
| US915 DR0 (SF10) | ~11 bytes | No |
| EU868 DR0 (SF12) | ~51 bytes | No |
| EU868 DR5 (SF7) | ~222 bytes | Apenas uno, quemando airtime |

Y el límite real no es el tamaño sino el **airtime**: ciclo de trabajo del 1% en
EU868, límites de dwell time en US915, y políticas de uso justo de ~30 s de
airtime por día por dispositivo en redes públicas.

### La consecuencia de diseño

Para que LoRaWAN sea viable, el evento necesita una **codificación binaria**:

| Campo | Binario | Nota |
|---|---|---|
| `tag_id` | 8 bytes | ISO 11784 es un código de 64 bits |
| `weight_kg` | 2 bytes | 0–2000 kg a resolución de 0.5 kg |
| `captured_at` | 4 bytes | epoch en segundos, no ISO-8601 |
| flags (`stable`, `source`) | 1 byte | |
| contador de evento | 2 bytes | |
| **Total** | **17 bytes** | 12× más chico que el JSON |

Nota lo que desaparece: **`device_id` y `event_id` no viajan**. El `device_id` es
el DevEUI del enlace, y el `event_id` se **deriva** de `DevEUI + contador` en
lugar de ser un UUID aleatorio.

### Regla para cualquier campo nuevo

> Antes de agregar un campo al contrato de eventos, pregunta si cabe en 17 bytes.
> Si no cabe, decide explícitamente si viaja **solo por LTE** y documenta por qué.

El contrato de datos es una **puerta de un solo sentido** (ver
[`engineering-rules.md`](engineering-rules.md)): cambiarlo después de que haya
estaciones en campo es caro. Ampliarlo sin pensar en el enlace más angosto es la
forma más fácil de cerrarnos LoRaWAN sin darnos cuenta.

### Lo que NO está decidido

Esto es un objetivo declarado, no un diseño aprobado. Falta:

- [ ] ¿LoRaWAN es transporte **primario** o respaldo cuando no hay LTE?
- [ ] ¿Red pública (TTN, Helium) o gateway propio?
- [ ] Banda regional: US915 para México, y qué implica en payload
- [ ] ¿El `event_id` derivado convive con el UUID actual, o lo reemplaza?
- [ ] Si el edge deja de ser una RPi y pasa a ser un MCU, el agent Python no aplica

Ninguna de esas se resuelve escribiendo código. Se resuelven con un Spike
(ver [`sprints.md`](sprints.md)) y una decisión tuya.

---

## Relacionados

- [`engineering-rules.md`](engineering-rules.md) — pilares y estándares
- [`hardware-boundary.md`](hardware-boundary.md) — frontera HW/SW y drivers
- [`edge-reliability.md`](edge-reliability.md) — supervivencia en campo
- [`testing.md`](testing.md) — qué y cómo se prueba
- [`unblock.md`](unblock.md) — cuando la causa raíz no aparece
- [`../data-contract.md`](../data-contract.md) — el contrato que esto restringe
