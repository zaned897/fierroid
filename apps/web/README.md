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

El destino ya apunta a la API de production. Si la URL de Cloud Run cambia
—porque se recree el servicio— hay que actualizarla aquí.

> Las *preview deployments* de Vercel usan este mismo `vercel.json`, así que
> apuntan a la API de **production**. Cuando exista `stage`, la salida limpia es
> un proyecto de Vercel aparte para esa rama, no condicionales aquí.

### Variables en Vercel

**Ninguna.** El client ID lo sirve la API en `GET /v1/auth/config` y la PWA lo
pide al cargar.

Antes venía de `VITE_GOOGLE_CLIENT_ID`, resuelto al construir. Eso significaba
el mismo valor en dos lugares y un modo de falla desagradable: si el build no
ve la variable, el minificador **elimina el efecto entero** que dibuja el botón
—puede probar que siempre retorna— y la página se ve bien, sin botón y sin
error en consola. Solo se detecta leyendo el bundle compilado.

Pidiéndolo en tiempo de ejecución hay una sola fuente de verdad, cambiarlo no
requiere reconstruir la PWA, y si algo falla se ve como lo que es: una petición
que falla.

`VITE_API_BASE` se deja **vacía**: con el rewrite, la API cuelga del mismo
origen y una base absoluta rompería esa ventaja.

### Orígenes autorizados en Google

El dominio de Vercel tiene que estar en **Orígenes autorizados de JavaScript**
del cliente OAuth, o el botón de Google no renderiza.
