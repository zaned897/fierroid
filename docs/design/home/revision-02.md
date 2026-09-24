# Revisión de la lámina 02

## Corrección de Funcionamiento y Beneficios

La versión anterior conservaba textos en lugar de iconos y fotografías con un
encuadre diferente. Su revisión no había demostrado la carga de las imágenes ni
la ausencia de desbordamiento móvil.

- Los tres pasos ahora muestran SVG de arete, báscula y nube, con conectores
  horizontales en escritorio y verticales en móvil.
- La fotografía nueva acerca al ganadero y al animal, y también sirve de fondo
  de la banda verde con el bovino hacia la derecha.
- La segunda tarjeta presenta un teléfono con una vista HTML de Pesajes. Los
  datos son estáticos y están rotulados como ejemplo; no hay controles falsos.
- La marca original, los textos y el acceso siguen la especificación funcional.
  Los botones «Nuevo pesaje», «Sincronizar» y la marca generada del mockup no se
  reproducen, conforme a las excepciones de frontend-home.md.

## Alcance pendiente

La ficha y gráfica de «Cada animal tiene su historia» aún corresponden a una
unidad posterior. Esta corrección no completa toda la lámina 02 ni todo el home.

## Validación

Chrome con viewport explícito de 375, 390, 768 y 1440 px: sin desbordamiento de
página, tres SVG presentes, fotografía cargada y sin excepciones JavaScript.
Capturas revisadas: [375 px](revision-02-375.jpg), [390 px](revision-02-390.jpg),
[768 px](revision-02-768.jpg) y [1440 px](revision-02-1440.jpg).
La aceptación visual del usuario sigue pendiente.

ESLint y build de Vite pasan ejecutados directamente desde `apps/web/node_modules`.
Los comandos `pnpm lint/build` abortan por
`ERR_PNPM_ABORTED_REMOVE_MODULES_DIR_NO_TTY`; no se reinstalaron dependencias.
