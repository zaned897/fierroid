# Acceso web compartido a stage

## Unidad actual — 2026-09-27

Objetivo aprobado: una URL estable para que los cuatro usuarios de pruebas
entren con Google y vean las estaciones de su organización, sin instalar el
frontend en cada PC. El agente de hardware sí se ejecuta localmente.

Criterios de esta unidad:

1. URL estable de stage accesible al equipo, con OAuth autorizado.
2. La web confirma el entorno desde la API y muestra STAGE antes y después del login.
3. Producción conserva su destino; usuarios normales conservan su alcance por organización.

## Implementado localmente

- `Entorno.jsx` consulta `/health` una vez al montar, sin credenciales, sin caché,
  con cancelación y timeout de 10 segundos. Stage y desarrollo muestran su entorno;
  producción no muestra franja. Fallos o respuestas desconocidas muestran un aviso
  de entorno sin confirmar; no se infiere el entorno del hostname.
- `vercel.json` reenvía `/health` igual que `/v1`: el host exacto
  `fierroid.vercel.app` a producción y los demás a stage.
- No se modificaron cuentas, permisos, registros de estaciones ni lecturas.
- Rama de trabajo: `codex/stage-shared-access`. Sin publicar.

## Verificación

- ESLint: pasó (`node_modules/.bin/eslint.cmd src --max-warnings 0`).
- Build Vite: pasó (`node_modules/.bin/vite.cmd build`).
- `http://localhost:5173/health`: HTTP 200, `env=stage`.
- Revisión visual pendiente: la herramienta del navegador rechazó la pestaña
  local por política de URL. No se intentó eludir el bloqueo.
- No se verificó un login Google de los cuatro usuarios.

## Acceso externo pendiente

La CLI de Vercel no está disponible ni se encontró su sesión en las ubicaciones
habituales. El navegador integrado abrió Vercel sin sesión. Se pidió al usuario
iniciar sesión allí para inspeccionar el proyecto.

GitHub confirma un preview exitoso del commit `0618389`:
`https://fierroid-ar5iti9zr-eduardo-santos-projects-b48d5c7a.vercel.app`.
Esto no demuestra que el equipo tenga acceso ni que OAuth esté autorizado.

Próximos pasos concretos:

1. Inspeccionar alias de la rama stage y protección del preview en Vercel.
2. Seleccionar la URL estable existente y comprobar `/health` y `/v1/auth/config`.
3. Autorizar exactamente su origen en el cliente OAuth de Google, conservando
   los orígenes existentes. No guardar secretos en esta documentación.
4. Publicar los cambios de esta unidad únicamente en preview/stage; no fusionar
   a main para probar, porque main despliega el frontend de producción.
5. Verificar Entrar, login real con usuario normal, estaciones y lecturas;
   revisar 375, 390, 768 y 1440 px y los estados de error del aviso de entorno.

## Unidades siguientes

- Panel: filtro por estación, hora de recepción, conexión y origen de prueba.
- Alta de estaciones por usuarios: código temporal, credencial por dispositivo
  y pertenencia a organización; hoy el endpoint de asignación exige superusuario.
- Detección de puertos y configuración recordada para simplificar el emparejamiento.

Estado: parcial; no anunciar una URL compartida operativa hasta verificar acceso y OAuth.

## Inspección de Vercel con sesión

- El usuario inició sesión y se verificó el proyecto `fierroid`.
- Alias estable observado: `fierroid-git-stage-eduardo-santos-projects-b48d5c7a.vercel.app`.
- `Vercel Authentication` está habilitado con `Standard Protection`: exige
  cuenta Vercel y pertenencia al equipo. No se cambió este ajuste.
- Existe la sección `Deployment Protection Exceptions` para exceptuar únicamente
  el alias stage. Abrir el formulario no respondió a los controles automatizados;
  no se guardó ninguna excepción. Su aplicación requiere confirmación por retirar
  una capa de autenticación en ese dominio. El login y alcance de Fierro se conservan.
- La UI actual indica **production como rama de despliegue de producción**.
  Esto corrige las notas históricas que atribuían ese despliegue a main.
- OAuth del alias stage todavía no verificado.

## Excepción aplicada con autorización explícita

El usuario autorizó retirar la protección adicional exclusivamente del alias
stage. Se completó el formulario con teclado y Vercel confirmó la excepción en
`Unprotected Domains`; `Require Log In` sigue activado para los demás previews.

Acceso compartido:
https://fierroid-git-stage-eduardo-santos-projects-b48d5c7a.vercel.app/entrar

Verificaciones posteriores:

- Sin cookies de Vercel, `/v1/auth/config` devuelve HTTP 200, `env=stage` y Google habilitado.
- La pantalla Entrar carga y renderiza el botón de Google.
- Se pidió al usuario completar un login con `eduardo@bitelemetric.com` para
  comprobar OAuth y acceso de usuario normal. Esa comprobación sigue pendiente.
- No se modificó el cliente OAuth ni se publicaron los cambios locales de la franja.
