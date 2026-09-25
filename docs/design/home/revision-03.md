# Revisión de preguntas frecuentes y acceso

Referencia: [03-preguntas-acceso.png](03-preguntas-acceso.png).
Textos y comportamiento: secciones 8 y 9 de [frontend-home.md](../../frontend-home.md).
Fecha: 2026-09-24.

## Resultado

Banda de privacidad con candado, acordeón blanco, cierre verde y pie marfil.
En escritorio, texto y acción del cierre van lado a lado; en móvil se apilan.
Se conserva la marca original. El texto sobre consultar nuevos datos con conexión
se incluye según la especificación, aunque sea más largo que el del mockup.

## Evidencia visual

- [375 px](revision-03-375.jpg)
- [390 px](revision-03-390.jpg)
- [768 px](revision-03-768.jpg)
- [1440 px](revision-03-1440.jpg)

Capturas del frontend local, no imágenes del mockup. Revisadas en los cuatro anchos.

## Comprobaciones ejecutadas

- Cuatro preguntas; primera abierta al cargar y restantes cerradas.
- Enter abre y Espacio cierra; otra pregunta abierta permanece abierta.
- Clic sobre la cabecera abre y cierra; indicador más/menos decorativo.
- Foco visible, controles de al menos 44 px y anclas existentes.
- Ancla del pie a FAQ desplaza el título a una zona visible.
- Ambos botones nuevos muestran el login existente; regreso al home operativo.
- Sin desbordamiento horizontal de página ni excepciones JavaScript.
- Contenido visible con preferencia de movimiento reducido.
- ESLint y build de Vite: correctos con los ejecutables de apps/web/node_modules.
- git diff --check: correcto.

No se probó autenticación con una cuenta ni el dashboard privado.
Historial sigue pendiente en una etapa separada. La aceptación visual final
corresponde al usuario.
