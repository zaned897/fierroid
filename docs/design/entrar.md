# Entrar — actualización visual

## Alcance

Solicitud: alinear el acceso con la identidad del home y llamarlo Entrar.
La ruta existente `/entrar` se conserva. No cambia ningún endpoint de la API,
proveedor, contrato de sesión ni condición de acceso por invitación.

## Diseño implementado

- Escritorio: paisaje del catálogo con velo verde, marca original y mensaje
  del home; panel marfil con título Entrar y botón oficial de Google.
- Hasta 800 px: una columna, sin paisaje, con marca, acceso y regreso al inicio.
- Colores locales: bosque `#143c2d`, petróleo `#176575`, marfil `#f7f8f3`.
- Estados de carga anunciados como status; errores visibles como alert.
- CSS limitado a `.entrar`; no se modifica Shell ni el panel privado.

## Verificación — 2026-09-24

- ESLint y Vite build directos desde node_modules: pasan.
- Chrome local a 375, 390, 768 y 1440 px: sin desbordamiento horizontal,
  título correcto, imagen cargada y botón real de Google presente.
- Capturas de 390 y 1440 px inspeccionadas visualmente.
- Volver al inicio mediante Enter: navega a `/`.
- Carga pendiente, proveedores vacíos y HTTP 503 comprobados mediante
  interceptación temporal de `/v1/auth/config` en el navegador de pruebas.
- Sin excepciones JavaScript en el recorrido responsive.

No se inició sesión en una cuenta real; intercambio de credenciales y vistas
autenticadas no verificados en este ciclo. Pendiente aceptación visual del usuario.
