# Anti *vibe coding*

Generar código a partir de una descripción vaga y aceptarlo porque compila.
Funciona los primeros días y deja un sistema que nadie entiende y que falla en
producción.

Este documento existe para que un agente **no pueda** trabajar así aquí.

---

## 1. Amnesia de contexto

> El agente olvida la estructura, duplica lógica y rompe lo que ya funcionaba.

El repo está indexado en un grafo de código consultable
(`codebase-memory`, en `http://localhost:9749`). **Consultarlo no es opcional
antes de escribir código nuevo.**

### Antes de escribir una función, preguntar si ya existe

| Pregunta | Herramienta |
|---|---|
| ¿Ya hay algo que haga esto? | `search_graph(query="verificar contrasena")` |
| ¿Dónde está definido `X`? | `search_graph(name_pattern="upsert_.*")` |
| ¿Quién llama a esto y qué rompo si lo cambio? | `trace_path(function_name="...", mode="calls")` |
| ¿Cómo está armado el sistema? | `get_architecture(aspects=["all"])` |
| Texto exacto en el código | `search_code(pattern="...")` |

Buscar cuesta segundos. Duplicar una función cuesta el resto del proyecto: dos
versiones de la misma lógica, una se arregla y la otra no.

> El índice puede estar viejo. `detect_changes` dice qué cambió desde la última
> indexación; `index_repository` la actualiza. Un grafo desactualizado miente
> con seguridad, que es peor que no tenerlo.

### Lo que además ya está escrito

Antes de proponer una regla o una convención, **leerla**: puede que ya exista.

- `CLAUDE.md` — invariante raíz y reglas no negociables
- [`product-principles.md`](product-principles.md) — cómo se construye aquí
- [`engineering-rules.md`](engineering-rules.md) — pilares y estándares
- [`../architecture.md`](../architecture.md) — a dónde va el sistema
- [`../data-contract.md`](../data-contract.md) — el contrato de eventos

---

## 2. Deuda técnica invisible

> Código frágil que se ve bien hasta que hay carga real.

### El contrato es un archivo, no una consecuencia

[`docs/contracts/openapi.json`](../contracts/openapi.json) está **versionado**.
Cambiar la superficie de la API obliga a actualizarlo en el mismo commit, y
[`test_contract.py`](../../apps/api/tests/test_contract.py) falla si no.

```bash
python -m fierro_api.contract           # regenerar tras un cambio deliberado
python -m fierro_api.contract --check   # verificar
```

Sin esto, un agente agrega, renombra o quita un campo y nadie se entera hasta
que el front deja de funcionar.

### Los tipos son parte del contrato

`mypy --strict` corre en pre-commit y en CI sobre `apps/` y `scripts/`. Una
función sin anotar, un genérico sin parámetros o un `Any` que se escapa de un
retorno tipado no pasan.

La única concesión es `ignore_missing_imports`, para no tener que escribir stubs
de `psycopg_pool` y `argon2` antes de poder verificar código propio. Las pruebas
quedan fuera: su valor ya lo da que pasen.

> `Any` que se escapa es la fuga más común. `json.load()` y una fila de base de
> datos devuelven `Any`, y si sale por un `return` tipado, contamina el tipo de
> todo lo que llame a esa función. Anotar la variable antes de devolverla, o
> convertir con `int(...)`, lo corta donde nace.

### El esquema va antes que la lógica

Para algo nuevo que persiste datos, el orden es: **migración SQL → prueba →
lógica**. No al revés. El esquema es una puerta de un solo sentido; la lógica
se reescribe en una tarde.

**Prohibido inventar campos** que no estén en el contrato o en una migración.
Si hace falta uno nuevo, se agrega ahí primero, donde se revisa.

---

## 3. Quema de tokens

> Apretar *regenerar* en bucle esperando que el error desaparezca.

Regenerar sin entender el error es la forma más cara de no arreglar nada.
[`product-principles.md` §5](product-principles.md) manda: reproducir, confirmar
la causa por dos caminos, prueba que falle, arreglar, prueba en verde.

### Atómico y verificable

1. Una función, una prueba, en verde
2. **No pasar al siguiente módulo con el actual en rojo.** Un rojo arrastrado
   se vuelve tres rojos que ya no se sabe cuál causó cuál
3. Si tras **3 intentos** el error sigue igual, no es un problema de generación:
   es estar atascado. Aplicar [`unblock.md`](unblock.md)

---

## 4. Pérdida de criterio

> El código parece magia y nadie del equipo puede explicarlo.

**Si no puedes explicar en dos minutos por qué un cambio funciona, no entra.**
Aplica igual a código escrito por un agente que por una persona.

Las tres barreras, en orden de cuándo actúan:

| Barrera | Cuándo | Qué detiene |
|---|---|---|
| `pre-commit` | antes del commit | Estilo, tipos, contrato desactualizado, skills desincronizadas |
| CI | en el PR | ruff, **mypy**, pytest contra Postgres real, build web, smoke de compose |
| Revisión humana | antes del merge | Todo lo demás |

Las dos primeras son automáticas y no se saltan. La tercera es la que atrapa
lo que ninguna herramienta ve: si la solución es la correcta.

`/code-review` sirve para una auditoría independiente antes de abrir el PR. Es
útil justamente porque llega sin el contexto de quien escribió el código.

---

## 5. Tamaño y forma de los archivos

La regla común de "máximo 100–200 líneas" **no aplica tal cual aquí**:
`main.py` y `auth.py` pasan de 400, y partirlos por número de líneas los dejaría
peor. El criterio real es la cohesión:

- Un archivo trata **un tema**. `auth.py` son credenciales; `animals.py` son
  fichas y fotos. Que sea largo no es el problema
- **Pasar de ~400 líneas es una señal**, no una prohibición: preguntarse si hay
  dos temas mezclados
- **Lo que se va a reemplazar vive aparte.** Las fotos están en su propio módulo
  y su propia tabla precisamente para que mudarlas sea acotado
- Una función que no cabe en pantalla probablemente hace dos cosas

---

## Checklist antes de escribir código

- [ ] ¿Busqué en el grafo si esto ya existe?
- [ ] ¿Leí la skill que aplica a lo que voy a tocar?
- [ ] Si persiste datos, ¿la migración y el contrato van primero?
- [ ] ¿Sé qué prueba va a demostrar que funciona?
- [ ] ¿Puedo explicar en dos minutos por qué es correcto?
- [ ] ¿Está dentro del alcance del ticket, o me estoy expandiendo?

## Relacionados

- [`product-principles.md`](product-principles.md) — elegancia, causa raíz, diseño
- [`engineering-rules.md`](engineering-rules.md) — pilares y estándares
- [`testing.md`](testing.md) — qué y cómo se prueba
- [`unblock.md`](unblock.md) — cuando el mismo error se repite
