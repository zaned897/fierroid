# Fierro PWA

Vite + React 19. Se despliega en **Vercel**.

## Desarrollo

```bash
corepack pnpm install
corepack pnpm dev
```

El proxy de `vite.config.js` manda `/v1` y `/health` a `http://127.0.0.1:8000`,
así que la API local se ve como si fuera el mismo origen.

Las variables salen del `.env` de la raíz del repo, no de este directorio: Vite
está configurado con `envDir: "../.."` para que la PWA y la API compartan un
solo archivo de configuración. **Vite no recarga `.env` en caliente**: después
de tocarlo hay que reiniciar `pnpm dev`.

## Despliegue en Vercel

En el proyecto de Vercel, **Root Directory** debe ser `apps/web`. Sin eso, el
build corre desde la raíz del monorepo y no encuentra nada.

### Por qué hay un rewrite de `/v1`

`vercel.json` reenvía `/v1/*` a la URL de Cloud Run. El efecto es que **la PWA
y la API comparten origen**, así que el navegador nunca hace una petición
cross-origin y CORS deja de ser algo que configurar y mantener sincronizado.

Las estaciones del corral no pasan por aquí: pegan directo a Cloud Run, y como
no son navegadores, CORS no les aplica.

Hay que reemplazar `REEMPLAZAR-CON-LA-URL-DE-CLOUD-RUN` por la salida `api_url`
de Terraform.

### Variables en Vercel

| Variable | Valor |
|---|---|
| `VITE_GOOGLE_CLIENT_ID` | El mismo ID de cliente OAuth de la API. Es público por diseño |

`VITE_API_BASE` se deja **vacía**: con el rewrite, la API cuelga del mismo
origen y una base absoluta rompería justamente esa ventaja.

### Orígenes autorizados en Google

El dominio de Vercel tiene que estar en **Orígenes autorizados de JavaScript**
del cliente OAuth, o el botón de Google no renderiza.
