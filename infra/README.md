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
terraform apply "-var-file=production.tfvars" -target='google_artifact_registry_repository.images[0]'
```

El `[0]` no es un detalle de escritura: **el registro es uno solo para el
proyecto**, y esta config se aplica una vez por entorno. Lo crea el entorno cuyo
`.tfvars` trae `crea_registro = true` —hoy `production`— y el resto lo leen con
un data source. Si los dos lo declararan como recurso, el segundo fallaría al
crear algo que ya existe; y si se importara, un `destroy` en `stage` se llevaría
las imágenes desde las que corre `production`.

Compartirlo en vez de dar uno a cada entorno es a propósito: `environments.md`
dice que nada entra a `production` sin pasar por `stage`, y eso solo se cumple
de verdad promoviendo **el mismo digest** que `stage` validó.

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

Antes, la clave de Anthropic del asistente. Terraform **lee** el secreto pero no
lo crea: así la clave no pasa por el `.tfvars` ni queda en claro en el estado.
Una vez por entorno (`stage`, `production`):

```bash
gcloud secrets create fierro-production-anthropic --replication-policy=automatic
echo -n "sk-ant-..." | gcloud secrets versions add fierro-production-anthropic --data-file=-
```

Sin el secreto el `plan` falla al leerlo. Para cambiar la clave basta otra
`versions add`; la API toma `latest` en el siguiente arranque.

```bash
terraform plan  "-var-file=production.tfvars"
terraform apply "-var-file=production.tfvars"
```

**Leer el `plan` antes del `apply`.** Es el único momento en que se ve qué se va
a crear y cuánto va a costar.

Para el otro entorno, el mismo ciclo con `terraform workspace new stage` y
`stage.tfvars`, **sin** el paso del registro: `stage` no lo crea, lo lee.

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

Lo de arriba es el arranque, se hace una vez. Lo de cada vez lo hace
[`deploy-api.yml`](../.github/workflows/deploy-api.yml): **promover la rama es
desplegar**.

```
push a stage      ─▶ CI verde ─▶ build ─▶ migraciones ─▶ servicio ─▶ /health ─▶ marca stage-ok-<sha>
push a production ─▶ CI verde ─▶ espera tu aprobación ─▶ el digest de stage-ok-<sha> ─▶ migraciones ─▶ servicio ─▶ /health
```

Promover sigue siendo lo de [`environments.md`](../docs/environments.md):

```bash
git checkout stage && git pull && git merge --ff-only origin/main && git push
# ...probar stage...
git checkout production && git pull && git merge --ff-only origin/stage && git push
```

El job de `production` se detiene en *Waiting for review*. Se aprueba en la
pestaña **Actions** del repo, en la corrida de *Deploy API*.

**La PWA no entra aquí:** Vercel la despliega sola al mergear a `main`. El
front va **por delante** de la API hasta que promueves. La PWA tolera una API
vieja a propósito — ver `normalizar()` en
[`apps/web/src/Login.jsx`](../apps/web/src/Login.jsx) — pero esa tolerancia se
escribe caso por caso.

### Se construye una vez, no una por entorno

**Una imagen por candidato a release.** Se construye desde el commit de
`stage`, se despliega ahí, y a `production` va **ese mismo digest**.
Reconstruir produce otra imagen, y entonces `production` corre algo que `stage`
nunca probó. Dos builds del mismo código ya dieron digests distintos.

Por eso el workflow etiqueta la imagen como `stage-ok-<sha>` **solo después**
de que stage respondió bien en `/health`, y `production` busca esa etiqueta.
Si el commit no pasó por stage, el job de production **falla** en vez de
construir.

### Quién es dueño de qué

Terraform es dueño de la infraestructura (secretos, variables, escalado,
permisos); el workflow solo cambia la **imagen**. `runtime.tf` ignora `image`,
así que `api_image` en los `.tfvars` solo cuenta al **crear** el servicio, y un
`apply` posterior no regresa a una imagen vieja.

Eso es lo que permite que CI no necesite el estado de Terraform ni los
`.tfvars`: las cadenas de Neon no salen de tu máquina. Terraform sigue siendo
manual, para los cambios de infraestructura, que son raros.

Para ver qué corre en cada entorno:

```bash
gcloud run services describe fierro-api-production --region northamerica-south1 \
  --format='value(spec.template.spec.containers[0].image)'
```

### A mano, si GitHub Actions no está disponible

El workflow usa [`scripts/deploy-api-cloud-run.sh`](../scripts/deploy-api-cloud-run.sh),
que corre igual con `gcloud` autenticado (en Git Bash o WSL):

```bash
IMG=northamerica-south1-docker.pkg.dev/fierro-caw-scale/fierro/fierro-api
docker build -f apps/api/Dockerfile -t "$IMG:manual" . && docker push "$IMG:manual"
# el push imprime el digest
./scripts/deploy-api-cloud-run.sh deploy stage "$IMG@sha256:..."
./scripts/deploy-api-cloud-run.sh verify stage "$IMG@sha256:..."
```

### Configuración inicial (una vez)

GitHub se identifica con Google por **Workload Identity Federation**: Google
confía en el token que GitHub emite para cada corrida, y no existe ninguna llave
JSON que guardar o que se pueda filtrar. Solo los jobs de este repo que corren
en los environments `stage` o `production` obtienen credenciales.

Requisito: los servicios de los dos entornos ya existen (`terraform apply` hecho
en `stage` y `production`).

**En Google Cloud**, en PowerShell, una sola vez:

```powershell
$PROJECT = "fierro-caw-scale"
$NUM = gcloud projects describe $PROJECT --format "value(projectNumber)"
$SA = "fierro-deployer@$PROJECT.iam.gserviceaccount.com"

gcloud services enable iamcredentials.googleapis.com sts.googleapis.com --project $PROJECT

# La identidad con la que despliega GitHub
gcloud iam service-accounts create fierro-deployer --project $PROJECT --display-name "Deploy de la API desde GitHub Actions"

# El puente con GitHub. La condicion acepta solo este repo (por id, que no
# cambia si alguien crea otro repo con el mismo nombre) y solo los dos environments.
gcloud iam workload-identity-pools create github --project $PROJECT --location global --display-name "GitHub Actions"
gcloud iam workload-identity-pools providers create-oidc fierroid --project $PROJECT --location global --workload-identity-pool github --issuer-uri "https://token.actions.githubusercontent.com" --attribute-mapping "google.subject=assertion.sub,attribute.repository=assertion.repository" --attribute-condition "assertion.repository_id == '1344345774' && assertion.sub in ['repo:zaned897/fierroid:environment:stage', 'repo:zaned897/fierroid:environment:production']"

gcloud iam service-accounts add-iam-policy-binding $SA --project $PROJECT --role roles/iam.workloadIdentityUser --member "principalSet://iam.googleapis.com/projects/$NUM/locations/global/workloadIdentityPools/github/attribute.repository/zaned897/fierroid"

# Lo minimo para desplegar: Cloud Run, subir imagenes al registro, y correr
# el servicio con la identidad que ya tiene cada entorno.
gcloud projects add-iam-policy-binding $PROJECT --role roles/run.developer --member "serviceAccount:$SA" --condition None
gcloud artifacts repositories add-iam-policy-binding fierro --project $PROJECT --location northamerica-south1 --role roles/artifactregistry.writer --member "serviceAccount:$SA"
gcloud iam service-accounts add-iam-policy-binding "fierro-api-stage@$PROJECT.iam.gserviceaccount.com" --project $PROJECT --role roles/iam.serviceAccountUser --member "serviceAccount:$SA"
gcloud iam service-accounts add-iam-policy-binding "fierro-api-production@$PROJECT.iam.gserviceaccount.com" --project $PROJECT --role roles/iam.serviceAccountUser --member "serviceAccount:$SA"

# Esto se copia a GitHub como GCP_WIF_PROVIDER
gcloud iam workload-identity-pools providers describe fierroid --project $PROJECT --location global --workload-identity-pool github --format "value(name)"
```

**En GitHub**, en *Settings* del repo:

1. *Environments* → **New environment** → `stage`. Sin reglas.
2. *Environments* → **New environment** → `production`. Marcar **Required
   reviewers** y agregarte. Esa es la aprobación de un clic.
3. *Secrets and variables* → *Actions* → pestaña **Variables** → *New
   repository variable*, dos veces:
   - `GCP_WIF_PROVIDER` = la salida del último comando
     (`projects/<número>/locations/global/workloadIdentityPools/github/providers/fierroid`)
   - `GCP_DEPLOY_SA` = `fierro-deployer@fierro-caw-scale.iam.gserviceaccount.com`

Son variables y no secretos porque no lo son: sin el token de GitHub de una
corrida de este repo, no sirven para nada.

No restringir los environments por rama (*Deployment branches*): el workflow
se dispara con `workflow_run`, que GitHub reporta como corrido desde `main`, y
una restricción a `production` lo bloquearía. Qué rama despliega a qué entorno
ya lo decide el propio workflow.

## Lo que NO incluye

Escrito para que no se descubra a mitad del despliegue:

- [ ] **Dominio propio.** Cloud Run da una URL `*.run.app` y Vercel una
      `*.vercel.app`. Mapear `app.fierro.mx` requiere verificar el dominio
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
