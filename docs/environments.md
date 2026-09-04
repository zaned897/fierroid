# Entornos y promoción

Tres entornos, tres ramas, una sola dirección de flujo.

| Entorno | Rama | Base de datos | Quién lo toca |
|---------|------|---------------|---------------|
| **dev** | cualquiera | SQLite local o el Postgres de `docker compose` | cualquiera, en su máquina |
| **stage** | `stage` | Postgres dedicado, datos sintéticos | promoción desde `main` |
| **production** | `production` | Postgres dedicado, datos reales | promoción desde `stage` |

## Flujo

```
feature branch ──PR──▶ main ──promoción──▶ stage ──promoción──▶ production
```

Nada entra a `stage` sin pasar por `main`, y nada entra a `production` sin pasar
por `stage`. Un commit directo a una rama de entorno **rompe CI a propósito**:
el job `promote-guard` falla si la rama tiene commits que no están en `main`.

Esa guardia existe porque el modelo de rama-por-entorno tiene un riesgo conocido:
alguien arregla algo urgente directo en `production`, y ese arreglo nunca vuelve
a `main`. La siguiente promoción lo pisa y el bug regresa. La guardia lo impide
en vez de confiar en que nadie lo haga.

## Promover

```bash
git checkout stage && git pull
git merge --ff-only origin/main
git push
```

```bash
git checkout production && git pull
git merge --ff-only origin/stage
git push
```

`--ff-only` es deliberado: si falla, es porque la rama divergió, y eso hay que
resolverlo a mano en vez de crear un merge commit que esconda el problema.

### Hotfix

No se parchea `production` directo. Va a `main`, se promueve a `stage`, y de ahí
a `production`. Si la urgencia no aguanta ese ciclo, el problema es que el ciclo
es lento — no que haya que saltárselo.

## Configuración por entorno

`FIERRO_ENV` vale `dev`, `stage` o `production`. En los dos últimos la API
**se niega a arrancar** si:

| Falta | Por qué aborta |
|-------|----------------|
| `FIERRO_API_DSN` | Sin Postgres guardaría en SQLite dentro del contenedor, que se borra al reiniciar. Perder pesajes en silencio es justo lo que el invariante raíz prohíbe |
| `FIERRO_API_CORS_ORIGINS` distinto de `*` | CORS abierto sobre una API con sesiones es un problema, no una comodidad |

Un `FIERRO_ENV` con typo (`prod` en vez de `production`) también aborta, en vez
de caer silenciosamente en modo `dev`.

`GET /health` devuelve el entorno, que es como el despliegue confirma que corre
la imagen esperada:

```json
{ "ok": true, "version": "0.1.0", "env": "stage" }
```

## Imágenes

CI verde en `main`, `stage` o `production` dispara [`publish.yml`](../.github/workflows/publish.yml),
que construye y sube a GHCR:

```
ghcr.io/zaned897/fierro-api:main       ghcr.io/zaned897/fierro-device:main
ghcr.io/zaned897/fierro-api:stage      ghcr.io/zaned897/fierro-device:stage
ghcr.io/zaned897/fierro-api:production ghcr.io/zaned897/fierro-device:production
ghcr.io/zaned897/fierro-api:sha-abc1234
ghcr.io/zaned897/fierro-api:latest     (solo desde production)
```

El disparo es por `workflow_run`, no por `push`: la imagen se publica **solo si
CI pasó** sobre ese commit. Publicar una imagen que no pasó pruebas es la forma
más común de desplegar algo roto.

> La primera vez, los paquetes de GHCR nacen privados aunque el repo sea público.
> Hay que hacerlos públicos una vez desde la página del paquete, o el `docker pull`
> pedirá credenciales.

## Dónde se despliegan

Cada pieza donde es más barata: **PWA en Vercel**, **Postgres en Neon**,
**API en Google Cloud Run**. Terraform (en [`infra/terraform/`](../infra/terraform))
cubre solo la parte de Google; Neon y Vercel se crean a mano una vez.

El costo estaba casi todo en la base de datos, no en la API: Cloud Run escala a
cero y cae en el nivel gratuito con tráfico de piloto.

El razonamiento completo, el costo aproximado y los pasos están en
[`infra/README.md`](../infra/README.md).

> ⚠️ **Nada se ha aplicado todavía.** Son archivos, no infraestructura viva.
> `terraform apply` crea recursos que se cobran.

Lo que sigue faltando, y está listado en el README de `infra/`:

- [ ] Hospedaje de la PWA y dominio propio
- [ ] Credenciales de CI hacia Google (Workload Identity Federation) para que
      las imágenes lleguen solas a Artifact Registry
- [ ] Monitoreo, alertas y presupuesto de gasto
- [ ] Backend remoto del estado de Terraform

## Relacionados

- [`docs/agent/testing.md`](agent/testing.md) — qué valida CI
- [`docs/architecture.md`](architecture.md) — a dónde va el sistema
