# Bitácora multimodal: decisión del spike (#143)

Épica #142. Este documento decide el modelo de datos del diario, dónde viven
fotos y audios, qué formatos se aceptan, con qué se procesan y cómo se busca.
Termina con texto listo para pegar en las hijas.

> **Costos aproximados.** Todos los precios se consultaron el **15 nov 2026** y
> pueden cambiar. Las cifras sirven para comparar opciones, no para presupuestar
> al centavo. Antes de comprometer un presupuesto, revisa la calculadora de cada
> proveedor. Fuentes en la sección [Precios usados](#precios-usados).

## Resumen de la decisión

| Pregunta | Recomendación | Alternativa descartada (por ahora) |
|---|---|---|
| 1. Modelo del diario | `journal_entries` por organización + `journal_entry_animals` (0..n), migración `011` que copia `animal_journal` y `animals.notes` con el mismo `entry_id` | Hacer `animal_id` nullable en `animal_journal` (no resuelve varios animales) |
| 2. Almacenamiento | Bucket de GCS privado por entorno en `northamerica-south1`. Subida **a través de la API** (valida bytes mágicos), lectura con **URL firmada de 5 min** | Seguir en Postgres (`BYTEA`): ~13 veces más caro por GB en Neon e infla el respaldo (#19) |
| 3. Formatos | Foto JPEG/WebP ≤ 1024 px y ≤ 2 MB. Audio WebM/Opus o MP4/AAC, ≤ 120 s y ≤ 2 MB | Aceptar cualquier `audio/*` o video |
| 4. Transcripción | Google Speech-to-Text V2, modelo Chirp 3, `es-MX`. Llamada síncrona al inicio; *dynamic batch* cuando pase de ~100 ranchos | OpenAI `gpt-4o-mini-transcribe` (mismo precio que batch, pero otro proveedor y otra llave) |
| 5. Descripción de fotos | Claude Haiku 5.5 con visión, **al subir** (job asíncrono), con el prompt de abajo | Generar al preguntar (la búsqueda no encontraría lo que no se ha descrito) |
| 6. Búsqueda | `tsvector` en español + `unaccent`, y que el asistente expanda la consulta con sinónimos | `pgvector` (requiere otro proveedor de embeddings; se reevalúa si #147 no pasa su set de preguntas) |
| 7. Privacidad y retención | Solo la organización ve sus adjuntos; se guardan mientras la cuenta esté activa; al cerrar, exportación y borrado a los 30 días | **Decisión del dueño** (ver opciones) |

---

## Lo que existe hoy (punto de partida)

- `animal_journal` (`migrations/007_animal_journal.sql`): nota atada a **un**
  animal (`animal_id NOT NULL`), cuatro categorías, append-only, idempotente
  por `entry_id`. Lógica en `journal.py`; rutas `POST/GET /v1/animals/{tag_id}/journal`.
- `animals.notes` (`006_animals.sql`): texto libre que se **sobrescribe**. La web
  (`Animales.jsx`) lo manda completo cada vez que guarda la ficha, junto con el alias.
- `animal_photos.bytes` (`006`): una foto por ficha en `BYTEA`, tope de 2 MB
  (`MAX_PHOTO_BYTES`), validación por bytes mágicos (`validate_photo`). La API
  hace de proxy al servir. #18 y #19 ya anticipan que esto no escala.
- `photo.js`: el teléfono reduce la foto a 1024 px de lado y la vuelve JPEG
  calidad 0.85 (~150 KB) antes de subirla.
- Infra (`infra/terraform`): Cloud Run en `northamerica-south1` con 1 CPU y
  512 MiB, Postgres en **Neon**, secretos en Secret Manager, jobs de Cloud Run
  (`migrate`, `waitlist_sheet`).
- Asistente (`asistente.py`) con `claude-haiku-5-5`, que ya lee la bitácora de
  un animal con la herramienta `bitacora(tag_id)`.

## Supuestos de volumen

Un **rancho** = una organización con 3 personas que anotan. Por rancho y por mes:

| Concepto | Supuesto | Resultado |
|---|---|---|
| Entradas | 10 al día | ~300 al mes |
| Entradas con foto | 40 %, 1.5 fotos cada una, ~180 KB por foto | ~180 fotos, ~32 MB |
| Entradas con audio | 20 %, 45 s promedio, ~300 KB (mezcla Opus 32 kbps y AAC) | ~60 audios, ~45 min, ~18 MB |
| Binarios nuevos | | **~50 MB al mes, ~0.6 GB al año** |
| Lecturas | cada adjunto se abre ~5 veces | ~1,200 descargas, ~240 MB |

Los costos de almacenamiento se calculan **al cumplir 12 meses** (0.6 GB por
rancho acumulados). Si el uso real es la mitad o el doble, los costos escalan
igual: todo es lineal.

---

## 1. Modelo del diario (#149)

### Tablas

```sql
-- Entradas a nivel organización. author_id es NULL solo en las notas migradas
-- de animals.notes, que nunca tuvieron autor.
CREATE TABLE journal_entries (
  entry_id    UUID PRIMARY KEY,
  org_id      BIGINT NOT NULL REFERENCES organizations (id) ON DELETE RESTRICT,
  author_id   BIGINT REFERENCES users (id) ON DELETE RESTRICT,
  occurred_at TIMESTAMPTZ NOT NULL,
  created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
  category    TEXT NOT NULL CHECK (category IN (
    'observacion','alimentacion','manejo','salud','clima','insumos','equipo','general')),
  body        TEXT NOT NULL CHECK (length(btrim(body)) > 0),  -- el tope de 4000 lo pone la API
  source      TEXT NOT NULL DEFAULT 'diario' CHECK (source IN ('diario','ficha')),
  UNIQUE (entry_id, org_id)
);

-- 0..n animales por entrada. Las llaves compuestas con org_id hacen imposible,
-- a nivel base, ligar una entrada con un animal de otra organización.
CREATE UNIQUE INDEX uq_animals_id_org ON animals (id, org_id);
CREATE TABLE journal_entry_animals (
  entry_id  UUID   NOT NULL,
  animal_id BIGINT NOT NULL,
  org_id    BIGINT NOT NULL,
  PRIMARY KEY (entry_id, animal_id),
  FOREIGN KEY (entry_id, org_id)  REFERENCES journal_entries (entry_id, org_id) ON DELETE CASCADE,
  FOREIGN KEY (animal_id, org_id) REFERENCES animals (id, org_id) ON DELETE RESTRICT
);
```

### Migración (idempotente aunque corra dos veces)

```sql
-- animal_journal -> diario: mismo entry_id, autor, occurred_at y created_at.
INSERT INTO journal_entries (entry_id, org_id, author_id, occurred_at, created_at, category, body)
SELECT j.entry_id, a.org_id, j.author_id, j.occurred_at, j.created_at, j.category, j.body
FROM animal_journal j JOIN animals a ON a.id = j.animal_id
ON CONFLICT (entry_id) DO NOTHING;
-- (y su fila en journal_entry_animals con ON CONFLICT DO NOTHING)

-- animals.notes -> una entrada 'general' por ficha, con id determinista
-- derivado del id del animal: la segunda corrida cae en el mismo id.
INSERT INTO journal_entries (entry_id, org_id, author_id, occurred_at, created_at, category, body, source)
SELECT md5('animals.notes:' || a.id)::uuid, a.org_id, NULL, a.updated_at, a.updated_at,
       'general', a.notes, 'ficha'
FROM animals a WHERE length(btrim(coalesce(a.notes, ''))) > 0
ON CONFLICT (entry_id) DO NOTHING;
```

Decisiones:

- **`animal_journal` queda congelada**, no se borra en #149: sirve de respaldo
  para revertir. Borrarla es un ticket aparte cuando el diario lleve un ciclo en
  producción.
- **`animals.notes` deja de escribirse.** Para no romper la web actual, el `PUT`
  de la ficha sigue aceptando `notes`, pero si el texto cambió lo guarda como
  entrada `general` con `source='ficha'` (con el autor de la sesión), y la ficha
  muestra la entrada `ficha` más reciente. Reenviar el mismo texto no crea nada.
  Así #150 puede quitar el campo cuando quiera, sin coordinar despliegues.
- **La nota migrada no se recorta.** El tope de 4000 caracteres vive en la API,
  no en la base, para no perder texto viejo más largo.
- **Rutas:** `POST/GET /v1/journal?org=&desde=&hasta=&tag=` a nivel
  organización, y las de `/v1/animals/{tag_id}/journal` siguen igual, como vista
  filtrada del mismo diario.

### Adjuntos (para #144)

```sql
CREATE TABLE journal_attachments (
  attachment_id UUID PRIMARY KEY,             -- generado en el cliente
  entry_id      UUID   NOT NULL,
  org_id        BIGINT NOT NULL,
  kind          TEXT   NOT NULL CHECK (kind IN ('photo','audio')),
  content_type  TEXT   NOT NULL CHECK (content_type IN
                  ('image/jpeg','image/webp','audio/webm','audio/mp4')),
  byte_size     INTEGER NOT NULL CHECK (byte_size BETWEEN 1 AND 2097152),
  duration_ms   INTEGER CHECK (duration_ms BETWEEN 1 AND 120000),
  sha256        BYTEA  NOT NULL,              -- detecta reintentos con otro archivo
  storage_key   TEXT   NOT NULL UNIQUE,       -- org/<org_id>/journal/<entry_id>/<attachment_id>
  created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
  FOREIGN KEY (entry_id, org_id) REFERENCES journal_entries (entry_id, org_id) ON DELETE RESTRICT,
  CHECK ((kind = 'audio') = (duration_ms IS NOT NULL))
);

-- Derivados (para #146): el original manda; esto es una ayuda con procedencia.
CREATE TABLE journal_derivatives (
  attachment_id UUID NOT NULL REFERENCES journal_attachments ON DELETE CASCADE,
  kind          TEXT NOT NULL CHECK (kind IN ('transcripcion','descripcion')),
  status        TEXT NOT NULL CHECK (status IN ('pendiente','listo','fallo')),
  text          TEXT,
  model         TEXT,           -- p. ej. 'chirp_3' o 'claude-haiku-5-5'
  model_version TEXT,
  error         TEXT,
  attempts      INTEGER NOT NULL DEFAULT 0,
  created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (attachment_id, kind)
);
```

El `storage_key` lleva solo ids, nunca nombres de rancho, aretes ni correos: si
una llave se filtra en un log, no dice de quién es.

---

## 2. Almacenamiento: GCS vs. Postgres

### Opciones

| | **A. Bucket GCS por entorno (recomendada)** | B. Seguir en Postgres (`BYTEA` en Neon) |
|---|---|---|
| Precio por GB al mes | ~$0.026 (Standard, `northamerica-south1`) | ~$0.35 (Neon Launch) |
| Respaldo | El dump de la base queda pequeño; el bucket tiene su propia protección (soft delete) | Los binarios viajan en cada dump y en el historial de PITR (#19) |
| Memoria de Cloud Run | La API no guarda binarios en memoria al servir | Cada lectura pasa por los 512 MiB del contenedor |
| Trabajo nuevo | Bucket y permisos en Terraform, dependencia `google-cloud-storage`, interfaz `Storage` con versión falsa para pruebas | Ninguno |
| Riesgo | Fotos en dos lugares durante la migración de `animal_photos` (#18) | Crece la base y el costo de forma silenciosa |

### Costo aproximado al mes, con 12 meses acumulados

| Ranchos | Datos guardados | A. GCS (almacenamiento + operaciones) | B. Postgres en Neon |
|---|---|---|---|
| 10 | 6 GB | ~$0.16 + ~$0.02 ≈ **$0.2** | ~$2.1 |
| 100 | 60 GB | ~$1.6 + ~$0.2 ≈ **$1.8** | ~$21 |
| 1000 | 600 GB | ~$15.6 + ~$1.7 ≈ **$17** | ~$210 (más el historial de PITR) |

Operaciones en GCS: ~240 escrituras (clase A, ~$0.05 por 10,000) y ~1,200
lecturas (clase B, ~$0.004 por 10,000) por rancho al mes.

**Salida de red (egress), igual en ambas opciones:** ~240 MB por rancho al mes
descargados a celulares. A ~$0.12/GB son ~$0.03 por rancho, **~$29 al mes con
1000 ranchos**. A esa escala pesa más que el almacenamiento, así que la
reducción en el cliente (`photo.js`) y el Opus a 32 kbps son las palancas de
costo, no el proveedor. Sirve también la regla de que la web pida la miniatura
y no el original cuando muestra listas (fuera de alcance aquí).

### Recomendación: A, con este flujo

1. **Subida a través de la API** (multipart, como la foto de hoy). Los archivos
   pesan ≤ 2 MB, muy por debajo del límite de petición de Cloud Run. La API
   valida bytes mágicos, tamaño y tipo **antes** de escribir el objeto, que es
   lo que pide #144. Con URLs firmadas de subida, la validación tendría que
   hacerse después de que el archivo ya está en el bucket. Se reconsidera solo
   si algún día se acepta video.
2. **Lectura con URL firmada (V4) de 5 minutos.** La API revisa que el adjunto
   sea de la organización del usuario y devuelve `{"url", "expires_at"}` en JSON.
   La web la pone directo en `<img src>` o `<audio src>`. Así el bucket no
   necesita CORS y el `Authorization` no viaja a Google.
3. Bucket privado, *uniform bucket-level access*, sin acceso público, metadatos
   `Content-Type` fijado por la API, `Content-Disposition: inline` y
   `Cache-Control: private, max-age=300`.
4. La cuenta de servicio de la API necesita `roles/storage.objectCreator` y
   `roles/storage.objectViewer` **sobre ese bucket**, y poder firmar con su propia
   identidad (`roles/iam.serviceAccountTokenCreator` sobre sí misma, para
   `signBlob`).
5. Variable `FIERRO_MEDIA_BUCKET` con la misma regla de falla ruidosa que
   `FIERRO_API_DSN`: en stage o production, sin bucket la API no arranca.
6. En desarrollo y pruebas, una implementación `LocalStorage` (carpeta) y una
   `FakeStorage` en memoria detrás de la misma interfaz.

Terraform propuesto (no se aplica en este spike):

```hcl
resource "google_storage_bucket" "media" {
  name                        = "fierro-media-${var.environment}-${var.project_id}"
  location                    = var.region          # northamerica-south1
  storage_class               = "STANDARD"
  uniform_bucket_level_access = true
  public_access_prevention    = "enforced"
  soft_delete_policy { retention_duration_seconds = 604800 }  # 7 días
}
```

`animal_photos` se migra al mismo bucket en #18, con el mismo módulo, cuando se
haga. No es requisito de esta épica.

---

## 3. Formatos y límites

| Tipo | Se acepta | Cómo se valida en la API | Límite |
|---|---|---|---|
| Foto | `image/jpeg`, `image/webp` | `FF D8 FF` o `RIFF....WEBP` | 2 MB, 1024 px de lado (la reducción la hace `photo.js`, que ya entrega JPEG 0.85) |
| Audio | `audio/webm` (Opus), `audio/mp4` (AAC) | WebM: `1A 45 DF A3`; MP4: `ftyp` en el byte 4 | 120 s y 2 MB |
| Por entrada | | | 6 fotos y 2 audios |

PNG ya no se guarda: `photo.js` lo convierte a JPEG. SVG, HTML, video y
cualquier otro tipo se rechazan con 400 aunque el `Content-Type` diga otra cosa.

**Qué graba cada navegador con `MediaRecorder`:**

- Chrome en Android graba `audio/webm;codecs=opus`.
- Safari en iOS graba `audio/mp4` (AAC). Las versiones recientes de Safari
  también reportan soporte de WebM/Opus, pero no hay que suponerlo.
- La web debe elegir con `MediaRecorder.isTypeSupported()` en este orden:
  `audio/webm;codecs=opus`, `audio/mp4`. Pedir `audioBitsPerSecond: 32000`
  (voz clara a ~240 KB por minuto) y detener la grabación sola a los 120 s.
- Con AAC y la tasa que Safari decida, 120 s pueden acercarse a 2 MB. Por eso el
  tope es de duración y de tamaño. Si en pruebas reales se pasa, se sube el tope
  de bytes, no el de duración.

`duration_ms` lo declara el cliente (leerlo en el servidor exigiría otra
dependencia). La API exige que esté entre 1 y 120000 y que el tamaño sea
coherente. La transcripción reporta la duración real y, si difiere mucho, el
job la registra.

---

## 4. Transcripción de audio en español

### Opciones

| Servicio | Precio aprox. por minuto | A favor | En contra |
|---|---|---|---|
| **Google Speech-to-Text V2, Chirp 3 (recomendada)** | ~$0.016 síncrono; ~$0.003 en *dynamic batch* (hasta 24 h); 60 min gratis al mes | Mismo proyecto de GCP: cuenta de servicio, sin llave nueva. Lee directo del bucket (`gs://`) | Hay que confirmar en qué regiones está Chirp 3 y si acepta MP4/AAC de Safari sin convertir |
| OpenAI `gpt-4o-mini-transcribe` | ~$0.003 | Barato, buena calidad en español | Proveedor y llave nuevos; el audio sale de GCP |
| Claude | — | — | La API de Claude no recibe audio |

### Costo aproximado al mes (~45 min por rancho)

| Ranchos | Minutos | Chirp 3 síncrono | Chirp 3 dynamic batch |
|---|---|---|---|
| 10 | 450 | ~$6 (después de los 60 gratis) | ~$1 |
| 100 | 4,500 | ~$72 | ~$14 |
| 1000 | 45,000 | ~$720 | ~$135 |

Recomendación: síncrono mientras haya menos de ~100 ranchos (el costo es bajo y
la transcripción llega en la siguiente corrida del job). Al crecer, *dynamic
batch*, si el dueño acepta que un audio tarde hasta un día en ser buscable.
Idioma `es-MX`, con `es-US` como alternativa si la región no tiene el primero.
Si Chirp 3 no acepta el MP4 de Safari, el job lo convierte a Opus con `ffmpeg`
en la imagen del job, no en la API.

### Cómo evaluar la calidad (pendiente: faltan los audios)

**Pendiente del dueño:** 3 notas de voz reales de campo (manga con ruido,
corral abierto con viento y una en interior), de 30 a 90 s, grabadas con los
celulares que usa el equipo. No se inventan resultados aquí.

Protocolo:

1. El dueño transcribe a mano cada audio (texto de referencia).
2. Se transcribe con Chirp 3 (`es-MX`) y, como comparación, con
   `gpt-4o-mini-transcribe`.
3. Se mide el WER (*word error rate*) normalizado (minúsculas, sin acentos ni
   puntuación) y, aparte, si salen bien los **términos clave**: números de
   arete, nombres de animales, medicamentos y cantidades.
4. Criterio de aceptación: WER ≤ 15 % y 100 % de números de arete correctos en
   los 3 audios. Si ninguno lo logra, la transcripción se muestra con aviso de
   baja confianza y se reevalúa.
5. El resultado se adjunta en el PR de #146.

---

## 5. Descripción de fotos con Claude (visión)

**Modelo:** `claude-haiku-5-5`, el mismo del asistente. **Cuándo:** al subir,
desde el job de derivados de #146, no al preguntar. La búsqueda (#147) solo
encuentra lo que ya está descrito, y una foto de 1024 px cuesta fracciones de
centavo.

### Costo por foto

Una imagen cuesta aprox. `ancho × alto / 750` tokens de entrada: una foto de
1024 × 768 son ~1,050 tokens. Con ~400 tokens de instrucciones y ~150 de
respuesta:

| Modelo | Precio (entrada / salida por millón de tokens) | Costo por foto | 1000 ranchos (~180,000 fotos al mes) |
|---|---|---|---|
| **Claude Haiku 5.5** | $0.10 / $0.50 | ~$0.0002 | **~$40 al mes** (~$20 con Batch API) |
| Claude Sonnet 5.5 | $2 / $10 | ~$0.0044 | ~$790 al mes |

Con 10 ranchos son ~$0.40 al mes; con 100, ~$4. Las instrucciones son
idénticas en cada llamada, así que el *prompt caching* reduce aún más la parte
de entrada cuando el prefijo alcanza el mínimo cacheable.

### Prompt propuesto

```text
Describe esta foto tomada en un rancho ganadero de México para que se pueda
encontrar después con una búsqueda en español. Responde en español, en 2 a 4
frases cortas y concretas.

Incluye solo lo que se ve:
- Qué hay: animal (especie, color, marcas, arete visible y su número si se lee),
  instalación, equipo, alimento, documento o paisaje.
- Condición visible: heridas, inflamación, secreciones, cojera aparente,
  condición corporal, estado de cercos o equipo.
- Texto legible (etiquetas de medicamentos, básculas, letreros), copiado tal cual.

No diagnostiques enfermedades ni recomiendes tratamientos. No adivines el
número de arete si no se lee completo: escribe "arete no legible". Si la foto
está borrosa u oscura, dilo.
```

La descripción se guarda en `journal_derivatives` con `model`, fecha y estado,
y la UI la muestra como "Descripción automática", nunca como texto del usuario.

---

## 6. Búsqueda: `tsvector` vs. `pgvector`

| | **`tsvector` en español (recomendada)** | `pgvector` con embeddings |
|---|---|---|
| Qué encuentra | Palabras y sus raíces ("vacunó" encuentra "vacuna") | Significado ("cojea" encuentra "renguea") |
| Proveedor nuevo | Ninguno (`unaccent` y `spanish` vienen con Postgres y Neon) | Sí: la API de Claude no genera embeddings; habría que sumar otro (p. ej. Voyage AI) con su llave |
| Espacio | Índice GIN, del orden del texto mismo | 1024 dimensiones × 4 bytes ≈ 4 KB por entrada: ~14 GB al año con 1000 ranchos (~$5 al mes por año de datos en Neon) |
| Latencia | Cada consulta filtra primero por `org_id`; con ~3,600 entradas por rancho al año, un GIN responde en pocos milisegundos | Bien con índice HNSW, pero hay que llamar al proveedor para la consulta (~100 ms o más) |

**Por qué basta `tsvector` para empezar:** quien busca es el asistente (#148),
y puede **expandir la consulta** antes de llamar a la herramienta ("cojera" →
`cojera | cojea | renguea | pata`). Eso cubre buena parte del hueco semántico
sin embeddings. Se reevalúa `pgvector` si #147 no logra que sus 5 preguntas de
ejemplo devuelvan la entrada correcta entre las 3 primeras.

Propuesta:

```sql
CREATE EXTENSION IF NOT EXISTS unaccent;
-- Wrapper IMMUTABLE para poder indexar (unaccent() es STABLE).
CREATE FUNCTION fierro_unaccent(text) RETURNS text
  LANGUAGE sql IMMUTABLE PARALLEL SAFE AS $$ SELECT public.unaccent('public.unaccent', $1) $$;

ALTER TABLE journal_entries ADD COLUMN search_text TEXT NOT NULL DEFAULT '';
ALTER TABLE journal_entries ADD COLUMN search_tsv tsvector
  GENERATED ALWAYS AS (to_tsvector('spanish', fierro_unaccent(body || ' ' || search_text))) STORED;
CREATE INDEX idx_journal_search ON journal_entries USING GIN (search_tsv);
```

`search_text` lo actualiza el job de derivados cuando llega una transcripción o
descripción, en la misma transacción que guarda el derivado.

---

## 7. Privacidad y retención (propuesta para el dueño)

Las notas de voz llevan la voz de los trabajadores y las fotos pueden mostrar
personas o placas: son **datos personales** bajo la LFPDPPP. Esto es una
propuesta, no una decisión técnica.

| Tema | Propuesta | Opciones para el dueño |
|---|---|---|
| Quién ve los adjuntos | Cualquier usuario de la organización, igual que las entradas. El superusuario solo con `?org=` explícito (soporte). Nunca hay URL pública; las firmadas duran 5 min | Restringir audios al autor y al dueño del rancho (requiere roles, que hoy no existen) |
| Cuánto se guardan | Mientras la cuenta esté activa. Append-only: no se editan; una corrección es otra entrada | Borrar audios a los 12 meses y conservar solo la transcripción (ahorra ~35 % del espacio) |
| Borrar un adjunto puntual | Solo por solicitud expresa (derechos ARCO o foto equivocada con datos sensibles), hecho por soporte, con registro de quién y cuándo | Permitir que el autor lo borre en las primeras 24 h |
| Cierre de cuenta | Exportación (entradas en JSON + adjuntos en un ZIP) disponible 30 días; después se borran objetos, derivados y filas. El *soft delete* del bucket (7 días) y el PITR de Neon terminan de expirar solos | Conservar 90 días en lugar de 30 |
| Terceros | Google (transcripción, mismo proyecto de GCP) y Anthropic (descripción). Hay que nombrarlos en el aviso de privacidad. **Verificar** en los términos vigentes de ambos que no usan los datos de la API para entrenar | Desactivar derivados por organización si el cliente lo pide |

---

## Precios usados

Consultados el **15 nov 2026**. Todos son aproximados y en USD.

| Concepto | Precio | Fuente |
|---|---|---|
| GCS Standard, `northamerica-south1` | ~$0.026 por GB al mes | [Cloud Storage pricing](https://cloud.google.com/storage/pricing) (tabla regional; la cifra se leyó en las versiones localizadas de la página y hay que confirmarla en la calculadora) |
| GCS operaciones clase A / clase B | ~$0.05 / ~$0.004 por 10,000 | [Cloud Storage pricing](https://cloud.google.com/storage/pricing) |
| Egress a internet, Norteamérica | ~$0.12 por GB (primer tramo) | [Cloud Storage pricing](https://cloud.google.com/storage/pricing) |
| Neon Launch: almacenamiento / cómputo | $0.35 por GB al mes / $0.106 por CU-hora; `pgvector` incluido | [neon.com/pricing](https://neon.com/pricing) |
| Speech-to-Text V2 Chirp 3 | ~$0.016 por min (primeros 500,000 min); *dynamic batch* ~$0.003 por min; 60 min gratis al mes | [Speech-to-Text pricing](https://cloud.google.com/speech-to-text/pricing) (las fuentes secundarias no coinciden en el precio de *dynamic batch*: $0.003 o $0.004) |
| OpenAI `gpt-4o-mini-transcribe` | ~$0.003 por min | Fuentes secundarias (p. ej. [costgoat.com](https://costgoat.com/pricing/openai-transcription)); no se verificó en la página de OpenAI |
| Claude Haiku 5.5 / Sonnet 5.5 | $0.10 / $0.50 y $2 / $10 por millón de tokens (entrada / salida) | [Claude pricing](https://platform.claude.com/docs/en/about-claude/pricing) |
| Tokens por imagen | ≈ ancho × alto / 750 | [Claude vision](https://platform.claude.com/docs/en/build-with-claude/vision) |

---

## Ajustes propuestos a las hijas (texto listo para pegar)

El dueño decide si los aplica. Cada bloque reemplaza o se agrega a la sección
indicada del issue.

### #149 · API: diario del rancho

> **Ajuste del spike (#143):** modelo final = `journal_entries` (por
> organización, `author_id` nullable solo para notas migradas, columna `source`
> `diario|ficha`) + `journal_entry_animals` con llaves compuestas `(…, org_id)`.
> `animal_journal` se congela (sin escrituras) y no se borra. El `PUT
> /v1/animals/{tag_id}` sigue aceptando `notes`, pero si el texto cambió lo
> guarda como entrada `general` con `source='ficha'` y la ficha devuelve la más
> reciente; `animals.notes` deja de escribirse. `desde` es inclusivo y `hasta`
> exclusivo, ambos con zona horaria.

### #150 · Web: pantalla Diario y fin del campo Notas

> **Ajuste del spike (#143):** la API ya convierte cada cambio de "Notas" en
> entrada del diario, así que quitar el campo no requiere migración ni
> coordinar despliegues. Las entradas con `source='ficha'` vienen con autor
> "Notas de la ficha" cuando son anteriores al diario. Para el filtro de fecha,
> mandar `desde`/`hasta` como medianoche local con su desfase (por ejemplo
> `2026-11-15T00:00:00-06:00`).

### #144 · API: adjuntos de foto y audio

> **Ajuste del spike (#143):**
> - `entry_id` referencia `journal_entries` (no `animal_journal`), con llave
>   compuesta `(entry_id, org_id)`. Rutas a nivel organización:
>   `POST/GET /v1/journal/{entry_id}/attachments` y
>   `GET /v1/journal/{entry_id}/attachments/{attachment_id}`, con `?org=` y
>   `_write_scope`.
> - Almacenamiento: bucket GCS privado por entorno (`FIERRO_MEDIA_BUCKET`, falla
>   ruidosa en stage/production), detrás de una interfaz `Storage` con
>   `GcsStorage`, `LocalStorage` y `FakeStorage`. Nueva dependencia
>   `google-cloud-storage`. Bucket y permisos en `infra/terraform` (objectCreator,
>   objectViewer y `serviceAccountTokenCreator` para firmar).
> - Subida **a través de la API** (multipart). Validar bytes mágicos antes de
>   escribir. Tipos: `image/jpeg`, `image/webp`, `audio/webm`, `audio/mp4`.
>   Límites: 2 MB por archivo, audio ≤ 120 s (`duration_ms` del cliente, 1 a
>   120000), máximo 6 fotos y 2 audios por entrada.
> - Guardar `sha256`: reintentar con el mismo `attachment_id` y el mismo archivo
>   devuelve lo guardado; con otro archivo, 409.
> - `GET …/{attachment_id}` devuelve `{"url", "expires_at"}` con URL firmada V4
>   de 5 minutos, emitida **después** de comprobar la organización.
> - `storage_key = org/<org_id>/journal/<entry_id>/<attachment_id>`, sin datos
>   personales.

### #145 · Web: adjuntar foto y nota de voz

> **Ajuste del spike (#143):** elegir el formato con
> `MediaRecorder.isTypeSupported()` en orden `audio/webm;codecs=opus`,
> `audio/mp4`; pedir `audioBitsPerSecond: 32000` y detener sola a los 120 s.
> Fotos con `reducirImagen` (JPEG). Para mostrar, pedir la URL firmada a la API
> y usarla directo en `<img>`/`<audio>` (sin `fetch` con credencial ni object
> URLs); si expira, pedir otra.

### #146 · API: transcripción y descripción automática

> **Ajuste del spike (#143):**
> - Audio: Google Speech-to-Text V2, modelo `chirp_3`, idioma `es-MX` (o `es-US`
>   si la región no lo tiene), leyendo `gs://` con la cuenta de servicio del job.
>   Confirmar regiones de Chirp 3 y soporte de MP4/AAC; si no lo acepta,
>   convertir a Opus con `ffmpeg` en la imagen del job.
> - Fotos: `claude-haiku-5-5` con el prompt de `docs/bitacora-multimodal.md`,
>   máximo 300 tokens de salida.
> - Se genera **al subir**: el job corre cada 5 min con Cloud Scheduler (o al
>   terminar cada subida), con `pg_advisory_lock`.
> - Tabla con `PRIMARY KEY (attachment_id, kind)`, `attempts` y máximo 3
>   reintentos. Al guardar un derivado `listo`, actualizar
>   `journal_entries.search_text` en la misma transacción.
> - Correr el protocolo de calidad con los 3 audios reales y adjuntarlo al PR.

### #147 · API: búsqueda en el diario

> **Ajuste del spike (#143):** primera versión con `tsvector` (`spanish` +
> `unaccent` con wrapper IMMUTABLE), columna generada sobre `body ||
> search_text` e índice GIN. Sin `pgvector` ni proveedor de embeddings. La
> función acepta consultas con `OR` (`websearch_to_tsquery`) para que el
> asistente mande sinónimos. Si el set de 5 preguntas no pasa, abrir un issue
> para evaluar `pgvector` con los números de este documento.

### #148 · Asistente responde con el diario

> **Ajuste del spike (#143):** en la descripción de la herramienta
> `buscar_bitacora`, pedir al modelo que expanda la consulta con sinónimos y
> formas regionales ("cojera", "cojea", "renguea"). Máximo 4 imágenes por
> respuesta, a 1024 px (~1,050 tokens cada una, ~$0.0004 de entrada con Haiku
> 5.5). Las imágenes se pasan como URL firmada o en base64 desde el bucket,
> nunca con URL pública.
