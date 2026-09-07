# Estado del proyecto

Dónde está todo y qué falta, para retomar desde cualquier máquina.
Actualizado el **6 de septiembre de 2026**.

El backlog vivo son los [issues](https://github.com/zaned897/fierroid/issues).
Este documento es lo que un issue no dice: qué está desplegado, qué no se ha
probado nunca, y qué te va a costar una tarde si no lo sabes.

## Qué está vivo

| | production | stage |
|---|---|---|
| API | `fierro-api-production-yj7cs5a7aq-pv.a.run.app` | `fierro-api-stage-yj7cs5a7aq-pv.a.run.app` |
| Front | `fierroid.vercel.app` | preview de la rama `stage` en Vercel |
| Base | Neon, rama `production` | Neon, rama `stage` |
| Datos | **vacío** | 3 organizaciones · 6 ranchos · 12 estaciones · 120 animales · 1 678 pesajes |
| Usuarios | 2 superusuarios | 2 superusuarios + 1 de organización |

Vercel despliega la PWA **sola al mergear a `main`**. Cloud Run se despliega a
mano; ver [`infra/README.md`](../infra/README.md).

## Lo que existe y nadie ha usado

- **El panel de administración funciona contra stage y nunca ha tocado datos
  reales.** Producción está vacía, así que la primera alta que hagas ahí será la
  primera vez que esas rutas escriben en la base real.
- **Nadie ha completado un login en stage** ([#58](https://github.com/zaned897/fierroid/issues/58)).
  El enrutamiento está probado, el botón se dibuja, pero no hay ninguna fila en
  `api_keys`. Hasta que alguien entre como usuario de organización, el
  aislamiento sólo está probado por tests.

## Deudas conocidas

| | |
|---|---|
| `POST /v1/readings` sin autenticación | Ticket **E0-T2**. Es la razón de que el rewrite de `vercel.json` mande a stage todo host que no sea exactamente `fierroid.vercel.app`: un preview no debe poder escribir en producción |
| Push a Artifact Registry manual | Hasta que exista Workload Identity Federation, cada despliegue de API depende de una máquina con Docker y Terraform |
| Estado de Terraform en local, sin cifrar | Contiene las cadenas de Neon en claro. El backend remoto está comentado en `infra/terraform/versions.tf` |
| Fotos de animales en Postgres | [#18](https://github.com/zaned897/fierroid/issues/18) y [#19](https://github.com/zaned897/fierroid/issues/19) |
| Dos pruebas sólo pasan con base vacía | [#57](https://github.com/zaned897/fierroid/issues/57) |

## Trampas del entorno

Cada una costó al menos un ciclo perdido.

**El venv deriva de los pins.** Un `mypy` local más nuevo que el de
`requirements-dev.txt` aprueba código que CI rechaza, porque resuelven los
genéricos distinto. `scripts/verificar_pins.py` corre en pre-commit y avisa; si
algo falla **sólo** en CI, comprobar primero la versión de la herramienta.

**Terraform 1.16 o mayor.** El estado de `production` lo escribió un 1.16.1 y
Terraform se niega a operar un estado escrito por una versión más nueva. `winget`
no llega: su manifiesto va detrás. Se baja del archivo de releases.

**PowerShell parte los argumentos con `=`.** `-var-file=x.tfvars` se corta y
Terraform responde `Failed to load ".tfvars" as a plan file`, que no se parece a
la causa. Van entre comillas.

**Una estación sin rancho hace invisibles sus lecturas.** La vista de animales
sale de `readings → devices → ranches → organizations`. Una lectura con un
`device_id` no registrado entra a la base y no aparece en ninguna vista, sin
error. Costó 837 pesajes que hubo que borrar. El panel de administración las
lista en rojo justo por esto.

**No confíes en `git log main..rama` para las ramas `cursor/*`.** Todo se mergea
con squash, así que git cree que hay decenas de ramas con trabajo sin mergear.
Es falso. La verdad está en `gh pr list --state all`.

**Dos agentes comparten el checkout.** Si hay más de un agente trabajando, cada
uno debe usar su propio worktree; si no, se cambian la rama entre ellos a media
sesión. Los servidores locales también necesitan puertos distintos.

## Credenciales

Sólo viven en archivos ignorados: `infra/terraform/*.tfvars` y el `.env` de la
raíz. Nunca en el chat ni en la salida de un comando — los scripts enmascaran y
muestran sólo el host. Un plan de Terraform guardado (`*.tfplan`) también las
lleva en claro, y por eso está en `.gitignore`.

En una máquina nueva hacen falta:

```
.env                              FIERRO_GOOGLE_CLIENT_ID, y el DSN si trabajas contra una base
infra/terraform/production.tfvars  sólo si vas a desplegar
infra/terraform/stage.tfvars       sólo si vas a desplegar
```

Sin ellos se puede desarrollar y correr las pruebas; no se puede desplegar.

## Trabajo en paralelo

Un segundo agente lleva el prototipo de RFID, en
[#45](https://github.com/zaned897/fierroid/issues/45) a
[#49](https://github.com/zaned897/fierroid/issues/49). El reparto:

| Suyo | Compartido y congelado | Nuestro |
|---|---|---|
| `apps/device-agent/**`, `hardware/**` | `docs/contracts/openapi.json` | `apps/api/**`, `apps/web/**`, `infra/**` |

El único archivo de frontera es
`apps/device-agent/src/fierro_device/hardware.py`, y sólo para añadir una rama
en `build_hardware()`.

## Relacionados

- [`infra/README.md`](../infra/README.md) — desplegar, y por qué cada pieza está donde está
- [`docs/environments.md`](environments.md) — promoción entre `main`, `stage` y `production`
- [`CLAUDE.md`](../CLAUDE.md) — el invariante raíz y las reglas no negociables
