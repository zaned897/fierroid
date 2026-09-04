# Infraestructura

Terraform para desplegar Fierro en **Google Cloud**: Cloud Run + Cloud SQL.

> ⚠️ **`terraform apply` crea recursos que se cobran.** Nada de este directorio
> se ha aplicado: son archivos, no infraestructura viva.

---

## Por qué Google Cloud

La decisión se tomó con una restricción por delante: **costo en un piloto**.

| Criterio | Por qué pesó |
|---|---|
| **Escala a cero** | Cloud Run no cobra sin tráfico. A escala piloto la API está ociosa casi todo el tiempo; en Fargate o App Runner se paga un contenedor encendido 24/7 que nadie usa |
| **Menos piezas** | Cloud Run necesita un servicio y una base. ECS necesita VPC, subredes, balanceador y NAT — cada uno con su costo fijo y su forma de romperse |
| **Región de Querétaro** | `northamerica-south1`. El salto de latencia importa desde un celular en el corral, no desde una oficina |
| **Terraform maduro** | El proveedor de Google es oficial y completo. El de Fly es comunitario e incompleto, y Render no tiene uno oficial — descartados justamente porque pediste Terraform |

### Lo que se pierde eligiendo Google

**MQTT administrado.** `docs/architecture.md` menciona AWS IoT Core como camino
posible de ingest a escala. Google retiró su IoT Core en 2023, así que en GCP
habría que correr EMQX o contratar un tercero.

No pesó en la decisión porque **MQTT sigue sin decidirse**, y elegir la nube por
un servicio que quizá nunca se use es exactamente la sobre-ingeniería que
`product-principles` prohíbe. Si MQTT administrado se vuelve un requisito duro,
esta decisión se revisa — y como todo va en contenedores, mudarse no es
reescribir.

---

## Qué crea

| Recurso | Para qué |
|---|---|
| Cloud SQL Postgres 16 | La base. Respaldos diarios; PITR solo en production |
| Cloud Run (servicio) | La API. Escala a cero por defecto |
| Cloud Run (job) | Las migraciones, separadas del arranque |
| Artifact Registry | Imágenes. **Cloud Run no despliega desde GHCR** |
| Secret Manager | El DSN, generado por Terraform y nunca escrito a mano |
| Cuenta de servicio | Identidad propia, con permiso al secreto concreto y a Cloud SQL |

### Decisiones que vale la pena conocer

**La contraseña de la base no la escribe nadie.** La genera `random_password`,
va a Secret Manager y la API la lee de ahí. Nunca pasa por un `tfvars`.

**Las migraciones son un job, no un paso de arranque.** Con varias instancias,
todas correrían las migraciones a la vez. El job corre una vez — y de todas
formas `fierro-api-migrate` toma un advisory lock.

**`deletion_protection` en production.** Un `terraform destroy` mal apuntado no
puede costar los pesajes de un cliente.

**El disco crece solo.** Un disco lleno deja de aceptar escrituras, que es
exactamente perder lecturas.

**La instancia tiene IP pública pero cero redes autorizadas.** El único camino
es el conector de Cloud SQL, que autentica con IAM. Apagar la IP sin montar una
VPC con peering deja la instancia inalcanzable incluso para el conector — y eso
`terraform validate` no lo detecta, falla al aplicar.

---

## Costo aproximado

Órdenes de magnitud, **no cotización**. Los precios cambian; verifica en la
calculadora de Google antes de comprometerte.

| Concepto | Aproximado |
|---|---|
| Cloud SQL `db-f1-micro` + 10 GB | ~10–15 USD/mes, encendida siempre |
| Cloud Run con `min_instances = 0` | Centavos a pocos dólares con tráfico de piloto |
| Artifact Registry, Secret Manager | Centavos |
| **Por entorno** | **~15–25 USD/mes** |

**El piso lo pone Cloud SQL**, que no escala a cero. Si quieres bajar de ahí,
la palanca es compartir una instancia entre `stage` y `production` usando dos
bases — más barato, a cambio de que compartan destino cuando algo falle.

`min_instances = 1` elimina el arranque en frío y agrega un contenedor
encendido 24/7. Vale la pena cuando alguien se queje, no antes.

---

## Cómo aplicarlo

### 1. Proyecto y APIs

```bash
gcloud projects create fierro-XXXXXX
gcloud config set project fierro-XXXXXX
gcloud services enable run.googleapis.com sqladmin.googleapis.com \
  artifactregistry.googleapis.com secretmanager.googleapis.com
```

Hace falta una cuenta de facturación asociada; sin ella Cloud SQL no se crea.

### 2. La primera imagen

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

### 3. Aplicar

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

### 4. Migrar y dar de alta al primer usuario

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

## Lo que NO incluye

Escrito para que no se descubra a mitad del despliegue:

- [ ] **Hospedaje de la PWA.** El front no se despliega aquí. Cloud Storage con
      CDN, o Firebase Hosting, es un ticket aparte
- [ ] **Dominio propio y certificado.** Cloud Run da una URL `*.run.app`; mapear
      `app.fierro.mx` requiere verificar el dominio
- [ ] **Credenciales de CI hacia Google.** Publicar imágenes desde GitHub Actions
      necesita Workload Identity Federation. Hoy el push a Artifact Registry es
      manual
- [ ] **Monitoreo y alertas.** No hay alerta si la API se cae o si la cola de una
      estación crece
- [ ] **Backend remoto del estado.** Está comentado en `versions.tf`. Mientras el
      estado sea local, **contiene la contraseña de la base en claro** en el
      disco de quien aplique
- [ ] **Presupuesto y alerta de gasto.** Conviene ponerla antes del primer apply

## Relacionados

- [`../docs/environments.md`](../docs/environments.md) — promoción entre entornos
- [`../docs/architecture.md`](../docs/architecture.md) — a dónde va el sistema
