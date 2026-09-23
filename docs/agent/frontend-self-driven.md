# Desarrollo incremental del frontend

Guía para que un agente de capacidad normal implemente una interfaz de Fierro por
etapas verificables, sin intentar completar todo el diseño en una sola sesión.

## Objetivo

Convertir una especificación aprobada en cambios pequeños, revisables y
reanudables. Cada ciclo termina con una unidad funcional, evidencia de validación
y un estado escrito que permita continuar sin depender del chat.

Esta guía controla el proceso. La especificación controla producto, textos y
apariencia. Para el home, la autoridad es [`frontend-home.md`](../frontend-home.md).

## Límites

- No implementar toda una pantalla en un solo ciclo.
- No cambiar API, autenticación, dashboard, administración ni hardware para
  facilitar una tarea visual.
- No inventar textos, datos, rutas, capacidades o estados.
- No usar los mockups como imagen final ni copiar sus errores accidentales.
- No desplegar, publicar ni promover ramas salvo petición explícita.
- Mantener el diff dentro de la unidad elegida. Las mejoras adyacentes quedan
  como pendientes, no entran al commit actual.

## Fuentes de verdad, en orden

1. `AGENTS.md` y las reglas de ingeniería.
2. La especificación versionada de la pantalla.
3. El comportamiento y los componentes existentes.
4. Los mockups, solo para composición y jerarquía.
5. Suposiciones del agente, solo para decisiones reversibles y menores.

Si dos fuentes se contradicen, detener la parte afectada y registrar el
conflicto. No resolver decisiones de producto por intuición.

## Unidad de trabajo

Una unidad debe poder revisarse de forma independiente y tocar un solo asunto:
tokens locales, encabezado, portada, vista ilustrativa, una sección, FAQ,
adaptación móvil o una revisión de accesibilidad.

Si requiere más de tres resultados verificables o mezcla estructura, contenido
y pulido general, dividirla antes de escribir código.

## Ciclo obligatorio

### 1. Orientar

- Leer la especificación completa la primera vez. Después, leer la sección
  actual y sus criterios relacionados.
- Consultar el grafo para localizar componentes y dependencias. Usar búsqueda
  textual para cadenas, CSS, configuración o si el grafo es insuficiente.
- Revisar `git status` y preservar archivos ajenos.
- Leer `docs/frontend-home-progress.md` si existe.

### 2. Elegir una sola unidad

Registrar antes de editar: resultado observable, archivos probables, criterios
aplicables y comprobación mínima. No comenzar una segunda unidad.

### 3. Implementar el mínimo vertical

- Reutilizar componentes, marca, imágenes y flujos existentes cuando encajen.
- Acotar estilos del home para no alterar otras pantallas.
- Preferir HTML semántico a abstracciones nuevas.
- Mantener datos de demostración estáticos y rotulados como ejemplo.
- No abstraer hasta que exista un segundo uso real o lo exija la especificación.

### 4. Verificar

Validar primero los criterios de la unidad. Al tocar código, ejecutar:

```bash
cd apps/web
pnpm lint
pnpm build
```

Para cambios visuales, revisar los anchos 375, 390, 768 y 1440 px indicados por
la especificación. Comprobar teclado, foco, anclas y login cuando sean afectados.
No afirmar que una validación pasó si no se ejecutó.

### 5. Dejar relevo

Crear o actualizar `docs/frontend-home-progress.md` con: unidad, estado,
resultado, archivos, validaciones ejecutadas, limitaciones, siguiente unidad y
pendientes fuera del ciclo. Distinguir terminado, parcial, bloqueado y no
verificado. Solo marcar terminado cuando la validación mínima pase.

## Orden recomendado para el home

1. Inspección y mapa de reutilización, sin cambios visuales.
2. Contenedor y tokens locales.
3. Encabezado y portada.
4. Vista ilustrativa.
5. Cómo funciona.
6. Beneficios e historial.
7. Privacidad y preguntas frecuentes.
8. Cierre y pie.
9. Adaptación móvil y accesibilidad integral.
10. Revisión contra todos los criterios.

No fusionar etapas para ahorrar turnos.

## Cuándo detenerse

Detenerse ante una decisión de producto ausente, contradicción entre fuentes,
expansión de alcance, recurso no autorizado o fallo previo que no pueda aislarse.
Tras tres intentos sobre el mismo bloqueo, aplicar `fierro-unblock`. Registrar
comando, error, hipótesis comprobadas y decisión requerida.

Una pausa correcta deja el árbol en un estado entendible. No se debe ocultar un
fallo, sustituir datos reales por datos inventados ni ampliar el alcance para
rodear el problema.

## Entrega completa

El frontend solo está completo cuando todos los criterios de la especificación
tienen evidencia, `pnpm lint` y `pnpm build` pasan, existen capturas finales
de escritorio y móvil, y no se observan regresiones en login, dashboard ni
administración. Completar una etapa no autoriza a declarar completa la página.
