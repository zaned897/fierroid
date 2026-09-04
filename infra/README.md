# Infraestructura

Cada pieza donde es más barata:

| Pieza | Dónde | Costo |
|---|---|---|
| **PWA** | Vercel | gratis |
| **Postgres** | Neon | nivel gratuito, escala a cero |
| **API** | Google Cloud Run | ~gratis a tráfico de piloto |

Terraform cubre solo la parte de Google. Neon y Vercel se crean a mano una vez.

> ⚠️ **`terraform apply` crea recursos que se cobran.** Nada de este directorio
> se ha aplicado: son archivos, no infraestructura viva.

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

### 1. Neon (la base)

Crear un proyecto en [neon.tech](https://neon.tech), región cercana a México.
Del panel salen **dos** cadenas de conexión: la que lleva `-pooler` en el host y
la que no. Ambas hacen falta, y no van al mismo lugar — ver arriba.

`sqladmin.googleapis.com` ya no se necesita: no hay Cloud SQL.

### 2. Proyecto de Google y APIs

```bash
gcloud projects create fierro-XXXXXX
gcloud config set project fierro-XXXXXX
gcloud services enable run.googleapis.com sqladmin.googleapis.com \
  artifactregistry.googleapis.com secretmanager.googleapis.com
```

Hace falta una cuenta de facturación asociada; sin ella Cloud SQL no se crea.

### 3. La primera imagen

Cloud Run solo despliega desde Artifact Registry. El repositorio lo crea
Terraform, así que la primera vez el orden es: aplicar, subir la imagen,
aplicar de nuevo con `api_image` apuntando a ella.

```bash
gcloud auth configure-docker northamerica-south1-docker.pkg.dev
docker pull ghcr.io/zaned897/fierro-api:production
docker tag ghcr.io/zaned897/fierro-api:production \
  northamerica-south1-docker.pkg.dev/fierro-XXXXXX/fierro/fierro-api:production
docker push northamerica-south1-docker.pkg.dev/fierro-XXXXXX/fierro/fierro-api:production
```

### 4. Aplicar

```bash
cp stage.tfvars.example stage.tfvars   # y editarlo
terraform init
terraform plan  -var-file=stage.tfvars
terraform apply -var-file=stage.tfvars
```

**Leer el `plan` antes del `apply`.** Es el único momento en que se ve qué se va
a crear y cuánto va a costar.

Los entornos se separan con workspaces:

```bash
terraform workspace new stage
terraform workspace new production
```

### 5. Migrar y dar de alta al primer usuario

```bash
gcloud run jobs execute fierro-migrate-stage --region northamerica-south1 --wait
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
