# Infraestructura

Cada pieza donde es más barata:

| Pieza | Dónde | Costo |
|---|---|---|
| **PWA** | Vercel | gratis |
| **Postgres** | Neon | nivel gratuito, escala a cero |
| **API** | Google Cloud Run | ~gratis a tráfico de piloto |

Terraform cubre solo la parte de Google. Neon y Vercel se crean a mano una vez.

> ⚠️ **`terraform apply` crea recursos que se cobran.**
>
> **`production` está aplicada y viva** desde el 4 de septiembre de 2026:
> <https://fierro-api-production-yj7cs5a7aq-pv.a.run.app>. **`stage` no** — su
> workspace no existe todavía, aunque `stage.tfvars` sí.

---

## Por qué así

**El costo estaba casi todo en la base de datos.** Cloud Run con `min_instances = 0`
cae dentro del nivel gratuito con tráfico de piloto; lo que no escalaba a cero era
Cloud SQL, a unos 10–15 USD/mes encendida siempre. Neon sí escala a cero y tiene
nivel gratuito, así que esa línea desaparece.

La PWA es un build estático: Vercel la sirve gratis, con CDN y despliegue
automático desde Git. No hay motivo para pagar por servirla.

**Por qué la API sigue en Cloud Run y no en Vercel:** es un contenedor con un
pool de conexiones, y en serverless el pool se arma y se tira en cada
invocación. Además el plan Hobby de Vercel es para uso no comercial, y esto va
a ser un SaaS.

### Lo que se pierde

**MQTT administrado.** `docs/architecture.md` menciona AWS IoT Core; Google
retiró su equivalente en 2023. No pesó porque **MQTT sigue sin decidirse**, y
elegir la nube por un servicio que quizá nunca se use es la sobre-ingeniería
que `product-principles` prohíbe.

**Tres facturas en vez de una.** Dos de ellas en cero, pero son tres paneles
donde mirar cuando algo falle.

**El nivel gratuito de Neon ronda 0.5 GB.** Con las fotos guardadas en Postgres
son unas 2,500 fotos antes de llenarse — el escenario del issue #18, que llegará
antes de lo previsto.

## Qué crea

| Recurso | Para qué |
|---|---|
| Cloud Run (servicio) | La API. Escala a cero por defecto |
| Cloud Run (job) | Las migraciones, separadas del arranque |
| Artifact Registry | Imágenes. **Cloud Run no despliega desde GHCR** |
| Secret Manager | Las dos cadenas de conexión de Neon |
| Cuenta de servicio | Identidad propia, con permiso solo a esos secretos |

**Terraform no crea la base.** Neon se crea a mano; Terraform solo guarda sus
cadenas de conexión como secretos.

### Decisiones que vale la pena conocer

**Hay dos cadenas de conexión, y la diferencia importa.** El pooler de Neon es
transaccional, y ahí el estado de sesión no sobrevive entre sentencias.
`fierro-api-migrate` toma un `pg_advisory_lock`, que es **de sesión**: por el
pooler se tomaría y soltaría en conexiones distintas, y dos migraciones
simultáneas correrían a la vez sin que nada las detuviera.

Por eso la API usa la cadena con `-pooler` y el job de migraciones la directa.
Confundirlas no da error: falla en silencio el día que dos despliegues coincidan.

**Las migraciones son un job, no un paso de arranque.** Con varias instancias,
todas migrarían a la vez.

**La contraseña nunca se commitea.** Va en un `.tfvars` local, que está en
`.gitignore`, y de ahí a Secret Manager.

## Costo aproximado

Órdenes de magnitud, **no cotización**. Verifica precios actuales antes de
comprometerte.

| Concepto | Aproximado |
|---|---|
| Vercel (PWA) | 0 en Hobby |
| Neon (Postgres) | 0 en el nivel gratuito |
| Cloud Run `min_instances = 0` | 0 a pocos dólares con tráfico de piloto |
| Artifact Registry, Secret Manager | centavos |
| **Por entorno** | **cerca de 0** |

Lo que rompe ese cero, en orden de probabilidad: pasarse de los 0.5 GB de Neon
por las fotos, poner `min_instances = 1`, o que el plan Hobby de Vercel no
aplique por ser un producto comercial.

## Cómo aplicarlo

**Terraform 1.16 o mayor.** El estado de `production` lo escribió un 1.16.1 y
Terraform se niega a operar un estado escrito por una versión más nueva que la
suya. Un binario más viejo falla con un error sobre el estado que no menciona
la palabra *actualizar*.

`winget` no sirve para esto: su manifiesto de `Hashicorp.Terraform` va detrás
de lo que HashiCorp publica, y a septiembre de 2026 topa en 1.15.8. Se baja
directo y se verifica la firma, porque es un binario que va a manejar
infraestructura:

```bash
curl -sLO https://releases.hashicorp.com/terraform/1.16.1/terraform_1.16.1_windows_amd64.zip
curl -sL https://releases.hashicorp.com/terraform/1.16.1/terraform_1.16.1_SHA256SUMS | grep windows_amd64
sha256sum terraform_1.16.1_windows_amd64.zip
```

### PowerShell parte los argumentos con `=`

Todos los comandos de abajo llevan `-var-file=...`. PowerShell lo corta en el
`=` y le pasa `.tfvars` suelto a Terraform, que responde
`Failed to load ".tfvars" as a plan file` — un error que no se parece en nada a
la causa. **Van entre comillas:**

```bash
terraform "-chdir=infra/terraform" apply "-var-file=production.tfvars"
```

En bash o zsh las comillas sobran y tampoco estorban.

### 1. Neon (la base)

Crear un proyecto en [neon.tech](https://neon.tech), región cercana a México.
Del panel salen **dos** cadenas de conexión: la que lleva `-pooler` en el host y
la que no. Ambas hacen falta, y no van al mismo lugar — ver arriba.

`sqladmin.googleapis.com` ya no se necesita: no hay Cloud SQL.

### 2. Proyecto de Google y APIs

```bash
gcloud projects create fierro-XXXXXX
gcloud config set project fierro-XXXXXX
gcloud services enable run.googleapis.com \
  artifactregistry.googleapis.com secretmanager.googleapis.com
```

Hace falta una cuenta de facturación asociada aunque todo apunte a cero: sin
ella Artifact Registry no acepta imágenes.

### 3. La primera imagen

Aquí hay un huevo-y-gallina: Cloud Run solo despliega desde Artifact Registry,
pero el repositorio lo crea Terraform. Se resuelve aplicando primero solo esa
pieza.

```bash
cd infra/terraform
terraform init
terraform workspace new production
terraform apply "-var-file=production.tfvars" -target=google_artifact_registry_repository.images
```

Después se construye y sube la imagen. **Directo desde el código, sin pasar por
GHCR**: los paquetes de GHCR nacen privados y haría falta autenticarse contra
dos registros en vez de uno.

```bash
gcloud auth configure-docker northamerica-south1-docker.pkg.dev

IMG=northamerica-south1-docker.pkg.dev/fierro-caw-scale/fierro/fierro-api:production
docker build -f apps/api/Dockerfile -t "$IMG" .
docker push "$IMG"
```

### 4. Aplicar todo lo demás

```bash
terraform plan  "-var-file=production.tfvars"
terraform apply "-var-file=production.tfvars"
```

**Leer el `plan` antes del `apply`.** Es el único momento en que se ve qué se va
a crear y cuánto va a costar.

Para el otro entorno, el mismo ciclo con `terraform workspace new stage` y
`stage.tfvars`.

> Si la región `northamerica-south1` no aceptara alguno de los servicios, el
> `plan` lo dirá. La alternativa es `us-central1`, más lejos pero con todo
> disponible.

### 5. Dar de alta al primer usuario

Las migraciones **ya están aplicadas** en las dos ramas de Neon. El job de
Cloud Run queda para los cambios de esquema futuros:

```bash
gcloud run jobs execute fierro-migrate-production --region northamerica-south1 --wait
```

El acceso es por invitación, así que sin un usuario dado de alta nadie entra:

```bash
gcloud run jobs create fierro-alta --region northamerica-south1 \
  --image <imagen> --command fierro-api-user \
  --args=--email,tu@correo.mx,--superuser
```

---

### 6. La PWA en Vercel

Importar el repo en Vercel con **Root Directory = `apps/web`**. La configuración
está en [`apps/web/vercel.json`](../apps/web/vercel.json) y hay que reemplazar
`REEMPLAZAR-CON-LA-URL-DE-CLOUD-RUN` por la salida `api_url` de Terraform.

Ese rewrite hace que la PWA y la API compartan origen, así que **el navegador
nunca hace una petición cross-origin** y CORS deja de ser algo que mantener.
Detalles en [`apps/web/README.md`](../apps/web/README.md).

Falta un paso fuera de aquí: agregar el dominio de Vercel a los **orígenes
autorizados** del cliente OAuth en Google, o el botón de inicio de sesión no
renderiza.

---

## Desplegar una versión nueva de la API

Lo de arriba es el arranque, se hace una vez. Esto es lo de cada vez, y es
manual mientras no exista Workload Identity Federation.

**La PWA no entra aquí:** Vercel la despliega sola al mergear a `main`. Eso
significa que el front siempre va **por delante** de la API durante el rato que
tardes en correr estos pasos. La PWA tolera una API vieja a propósito — ver
`normalizar()` en [`apps/web/src/Login.jsx`](../apps/web/src/Login.jsx) — pero
esa tolerancia se escribe caso por caso, así que un cambio de contrato que la
PWA ya use rompe el login hasta que la API salga.

```bash
git checkout production && git merge --ff-only origin/stage && git push
```

Se construye desde ese árbol, no desde la rama en la que estabas:

```bash
IMG=northamerica-south1-docker.pkg.dev/fierro-caw-scale/fierro/fierro-api:production
docker build -f apps/api/Dockerfile -t "$IMG" .
docker push "$IMG"
```

**Comprobar el código dentro de la imagen, no que el build pasara.** Ya nos
pasó desplegar una imagen que compilaba y a la que le faltaba una dependencia:

```bash
docker run --rm --entrypoint python "$IMG" -c "import fierro_api.main"
```

El `push` imprime el digest. Va a `production.tfvars`, en `api_image`, con
`@sha256:...` en lugar de `:production`. **Con la etiqueta móvil Terraform no ve
ningún cambio y Cloud Run se queda con la imagen anterior**, sin decir nada.

```bash
terraform "-chdir=infra/terraform" apply "-var-file=production.tfvars"
```

Sale `2 to change, 0 to destroy`: el servicio y el job. Si hay migraciones
nuevas, además `gcloud run jobs execute fierro-migrate-production --region
northamerica-south1 --wait`.

Se verifica contra el origen que usa el navegador, no contra `*.run.app`, que
es el que puede estar mal:

```bash
curl -s https://fierroid.vercel.app/v1/auth/config
```

## Lo que NO incluye

Escrito para que no se descubra a mitad del despliegue:

- [ ] **Dominio propio.** Cloud Run da una URL `*.run.app` y Vercel una
      `*.vercel.app`. Mapear `app.fierro.mx` requiere verificar el dominio
- [ ] **Credenciales de CI hacia Google.** Publicar imágenes desde GitHub
      Actions necesita Workload Identity Federation. Hoy el push a Artifact
      Registry es manual
- [ ] **Monitoreo y alertas.** No hay aviso si la API se cae o si la cola de una
      estación crece
- [ ] **Respaldos de Neon.** El nivel gratuito tiene restauración limitada en el
      tiempo. Antes de tener datos de un cliente real, revisar qué cubre
- [ ] **Backend remoto del estado.** Está comentado en `versions.tf`. Mientras
      sea local, **contiene las cadenas de conexión en claro** en el disco de
      quien aplique
- [ ] **Alerta de gasto.** Aunque todo apunte a cero, ponerla antes del primer
      apply cuesta dos minutos

## Relacionados

- [`../docs/environments.md`](../docs/environments.md) — promoción entre entornos
- [`../docs/architecture.md`](../docs/architecture.md) — a dónde va el sistema
