# Demo en vivo de "Pregúntale a tu hato"

Cómo dejar el asistente funcionando de punta a punta en **stage**, con un rancho
de demostración cuyos pesajes sí cuentan.

## Por qué hace falta un rancho aparte

Los datos que ya hay en stage los sembró `seed_synthetic.py`, que marca cada
pesaje con `source="synthetic"`. El asistente descarta esos pesajes a propósito
(`hato.es_prueba`): nunca presenta pruebas como si fueran ganado. Contra esos
ranchos contestaría "no tienes animales pesados".

[`scripts/seed_demo_hato.py`](../scripts/seed_demo_hato.py) crea una
organización propia, **Rancho El Mezquite (demo)**, con pesajes `source="demo"`
que sí cuentan. Todo pasa por la API pública, con la llave de un superusuario.

## Lo que carga

38 animales en recría y engorda en El Mezquite, Fresnillo, Zac.: 36 pesados
cada semana durante 14 semanas en dos estaciones (manga y corral), unos 440
pesajes, 11 fichas con alias y notas, y 9 anotaciones de bitácora. Los aretes
salen de la semilla y no cambian entre corridas.

| Animal | Arete | Qué cuenta |
|---|---|---|
| El Pinto | 484876239146702 | Dejó de ganar hace 4 jornadas. Bitácora: neumonía, tratamiento |
| La Güera | 484580203058465 | Lleva 3 jornadas sin ganar. Bitácora: cojera por una espina. Ganancia más baja del hato |
| Canelo | 484399777785667 | Su último pesaje es atípico (dos becerros en la plataforma). Queda fuera del total |
| La Mora | 484429633116415 | No se pesa desde hace 6 semanas: se fue al potrero de La Mesa |
| (sin alias) | 484737705937575 | No se pesa desde hace 5 semanas |
| El Prieto | 484575254976867 | Solo tiene pesajes inestables: queda fuera del total |
| Lucero | 484929109849606 | Tiene ficha y todavía no se pesa |
| (sin alias) | 484889577014195 | Tiene ficha y todavía no se pesa |
| El Güero | 484837347256033 | El mejor de la engorda, más de 450 kg, un atípico viejo marcado en su ficha |
| Tornado | 484373852626231 | Más de 450 kg, lote de finalización |
| El Colorado, La Pinta | | Crecen normal, para preguntar por alias |

El resto crece sin novedad. Las pruebas de
[`test_seed_demo_hato.py`](../apps/api/tests/test_seed_demo_hato.py) corren las
mismas cuentas del asistente sobre estos datos y fallan si la historia deja de
verse, con cualquier fecha de siembra.

## Guion de preguntas

| Pregunta | Qué debe encontrar |
|---|---|
| ¿Cuántas vacas tengo registradas? | 38 registradas, 36 pesadas, 2 con ficha sin pesaje |
| ¿Cuál es el peso total hasta hoy? | Suma de 34 animales; dice que Canelo y El Prieto quedan fuera y por qué |
| ¿Qué vaca tiene problemas? | El Pinto y La Güera sin ganar, Canelo con pesaje atípico, La Mora y otra sin pesar |
| ¿Qué le pasó a El Pinto? | Su ficha: pesajes, ganancia y la bitácora de la neumonía |
| ¿Cuáles pasan de 450 kg? | El Güero y Tornado |
| ¿Cuál gana menos peso? | La Güera |
| ¿De qué raza es Tornado? | Lo lee de las notas de su ficha |
| ¿Cuánto vale el becerro en Fresnillo? | "Solo puedo contestar sobre tu hato…" |
| Borra a Canelo | Dice que solo lee datos |

## Pasos, en orden

### 1. La clave de Anthropic en Cloud Run

Sin `ANTHROPIC_API_KEY` el asistente responde 503 ("falta configurar
ANTHROPIC_API_KEY"). Va por Terraform, como las cadenas de Neon. Ponerla a mano
con `gcloud run services update` no sirve: el siguiente `apply` la quitaría.

1. Crea una clave en [console.anthropic.com](https://console.anthropic.com),
   en **API Keys**, y ponle un límite de gasto mensual. La API ya topa a 200
   preguntas por rancho al día (`FIERRO_ASISTENTE_LIMITE_DIARIO`).
2. Agrégala a tu `infra/terraform/stage.tfvars` local (está en `.gitignore`):

   ```hcl
   anthropic_api_key = "sk-ant-..."
   ```

3. Aplica. El `plan` debe mostrar 3 recursos nuevos (secreto, versión y
   permiso) y el servicio cambiando:

   ```bash
   terraform "-chdir=infra/terraform" plan  "-var-file=stage.tfvars"
   terraform "-chdir=infra/terraform" apply "-var-file=stage.tfvars"
   ```

### 2. Que stage corra una imagen con el asistente

El asistente llegó en #112. Si la imagen de stage es anterior, `/v1/asistente`
no existe:

```bash
curl -s -o /dev/null -w "%{http_code}\n" -X POST \
  https://fierro-api-stage-yj7cs5a7aq-pv.a.run.app/v1/asistente
```

`401` o `422` = el endpoint existe. `404` = hay que desplegar con el ciclo de
siempre de [`infra/README.md`](../infra/README.md#desplegar-una-versión-nueva-de-la-api):
construir desde `stage`, `docker push`, poner el digest en `api_image` y
`apply`. Se puede hacer en el mismo `apply` del paso 1.

### 3. Tu llave de superusuario

Entra a la PWA de stage con tu cuenta y, en la consola del navegador:

```js
JSON.parse(localStorage.getItem("fierro.session")).api_key
```

Es revocable desde la API (`DELETE /v1/auth/keys/{id}`) o cerrando sesión en
todos lados.

### 4. Sembrar

```bash
export FIERRO_TOKEN="<la llave del paso 3>"
python3 scripts/seed_demo_hato.py \
  --api https://fierro-api-stage-yj7cs5a7aq-pv.a.run.app \
  --usuario <otra-cuenta>@gmail.com
```

Solo usa stdlib. Crea la organización, el rancho, las dos estaciones, los
pesajes, las fichas, la bitácora y da de alta a `--usuario` en el rancho demo.

- **Siémbralo la víspera o el mismo día de la demo.** La última jornada es ayer
  por omisión, y "no se pesa desde hace 30 días" se cuenta contra hoy.
- **Repetirlo no duplica nada.** Sembrar el mismo rancho con otra fecha
  mezclaría dos historias, y el script se detiene con error. Para una demo
  semanas después, siembra otro rancho: `--org demo-el-mezquite-2`.
- **Se niega a correr contra production**, salvo con `--permitir-produccion`.

### 5. Entrar con la cuenta de la demo

**El superusuario no puede usar el asistente desde la PWA:** la API le pide que
diga de qué rancho habla (`?org=`) y la pantalla no lo manda. Por eso la demo se
hace con una cuenta de organización, la de `--usuario`.

Tiene que ser **otra cuenta de Google**, no la tuya. El alta es por correo y
reescribe la cuenta: darte de alta en el rancho te quitaría el superusuario. El
script se niega si le pasas tu propio correo.

Con esa cuenta, en la PWA de stage: **Pregúntale** y el guion de arriba.

## Si algo falla en vivo

| Lo que ves | Causa |
|---|---|
| "falta configurar ANTHROPIC_API_KEY" | Paso 1 sin aplicar, o el servicio no reinició con el secreto |
| "Como superusuario, indica la organización" | Entraste con tu cuenta, no con la de la demo |
| "Tu cuenta no tiene organización asignada" | El paso 4 corrió sin `--usuario` |
| "no tienes animales pesados" | La cuenta está en un rancho sembrado con `seed_synthetic.py` |
| "Ya se hicieron las 200 preguntas de hoy" | Cupo diario; se reinicia con la API o al día siguiente |
| Ningún botón de Google en stage | Falta `FIERRO_GOOGLE_CLIENT_ID` en stage o el origen en el cliente OAuth ([#58](https://github.com/zaned897/fierroid/issues/58)) |
