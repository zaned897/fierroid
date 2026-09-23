# Home de Fierro: guía de implementación y continuidad

Estado: dirección visual acordada; frontend todavía sin implementar.
Fecha: 2026-09-22.
Audiencia: modelo o desarrollador que retome el trabajo sin acceso al chat.

## 1. Objetivo y alcance

Rediseñar la página pública de inicio para explicar Fierro de forma sencilla a
personas que trabajan con ganado y facilitar el acceso de usuarios existentes.
Debe mostrar el producto desde la portada, conservar la identidad del proyecto
y evitar lenguaje técnico, promesas absolutas y exceso de información.

Esta tarea comprende el home y sus adaptaciones a escritorio y móvil. No incluye
reescribir el dashboard, login, API, drivers, permisos o despliegues. La vista de
Pesajes que aparece en el home es una demostración, no una conexión a datos reales.
El rediseño funcional de Pesajes está en [frontend-pesajes.md](frontend-pesajes.md).

## 2. Referencias visuales y autoridad

Mockups versionados junto a esta guía:

1. [Portada con azul petróleo](design/home/01-portada.png).
2. [Funcionamiento y beneficios](design/home/02-funcionamiento-beneficios.png).
3. [Preguntas frecuentes y acceso](design/home/03-preguntas-acceso.png).

Las imágenes comunican composición y jerarquía. Este documento prevalece sobre
textos, datos, logotipos y controles accidentales generados en las imágenes.
No implementar el mockup completo como una imagen: usar HTML semántico y CSS.

### Diferencias de las imágenes que NO deben implementarse

- Conservar la marca original de `Marca.jsx` y sus recursos. No sustituirla por
  las diferentes vacas o cabezas de toro generadas en las láminas 02 y 03.
- No añadir Probar Fierro, registro público, Recursos, Contacto o una segunda
  navegación porque aparezcan en la lámina 02.
- No añadir botones Nuevo pesaje o Sincronizar de los teléfonos ilustrados.
  La captura y sincronización continúan siendo automáticas.
- No introducir campos de raza, sexo ni aretes adicionales a partir de las
  fichas inventadas de la lámina 02.
- No repetir el cierre promocional de la lámina 02. Hay un solo cierre, descrito
  en la sección 9 de este documento.
- Ningún dominio, usuario, dato de ejemplo o imagen generada acredita un cliente
  real ni una funcionalidad ya implementada.

## 3. Identidad visual acordada

| Uso | Dirección |
|---|---|
| Base oscura | Verde bosque, referencia #143C2D; conservar coherencia con los verdes existentes. |
| Fondo principal | Marfil claro, referencia #F7F8F3, y blanco para superficies. |
| Acento | Azul petróleo, referencia #176575, para acciones, enlaces, iconos y gráfica. |
| Texto | Verde muy oscuro y grises con contraste suficiente. |
| Tipografía | Reutilizar Inter instalada en el proyecto. |

El usuario descartó café, dorado, ocre y mostaza como acentos de interfaz.
Los colores naturales de las fotografías no necesitan eliminarse.
Validar contraste de combinaciones reales; los hexadecimales son referencias,
no una garantía de accesibilidad. Evitar degradados decorativos en cada control.

Aplicar los nuevos tokens al home mediante un contenedor propio. No reemplazar
variables globales de forma que cambien login, administración o dashboard sin
haber incluido esas pantallas en el alcance. La especificación anterior de
Pesajes menciona ocre: aquí la decisión posterior de azul petróleo rige el home
y su vista ilustrativa; no implica modificar automáticamente la aplicación.

## 4. Estructura y encabezado

Orden único de la página:

1. Encabezado y portada.
2. Cómo funciona: tres pasos.
3. En el corral y desde tu celular.
4. Cada animal tiene su historia.
5. Privacidad y acceso del equipo.
6. Preguntas frecuentes.
7. Cierre de acceso y pie de página.

| Etiqueta | Acción |
|---|---|
| FIERRO | Marca original; enlace al inicio de la página si es interactiva. |
| Cómo funciona | Ancla #como-funciona. |
| Beneficios | Ancla #beneficios. |
| Preguntas frecuentes | Ancla #preguntas-frecuentes. |
| Iniciar sesión | Usar el flujo existente, hoy mediante onEntrar. |

En móvil, mantener visible Iniciar sesión; Entrar es una abreviación aceptable
solo si el ancho lo exige. No esconder la única entrada detrás de un menú.
Los enlaces secundarios pueden omitirse del encabezado móvil: no agregar un
menú hamburguesa sin contenido necesario. Ofrecer Saltar al contenido para teclado.

## 5. Portada — lámina 01

| Elemento | Texto canónico |
|---|---|
| Lema | Del corral a tu bolsillo. |
| H1 | El peso de tu ganado, siempre a la mano. |
| Descripción | Registra cada pesaje y consulta el historial de tus animales desde tu celular. |
| Acción principal | Iniciar sesión |
| Acción secundaria | Conocer Fierro |
| Nota | Acceso por invitación. |
| Pie de demostración | Vista de ejemplo |

Conocer Fierro desplaza a #como-funciona. La portada no necesita ocupar una altura
mínima de una pantalla completa: dejar que el contenido y dispositivo determinen
la altura. Escritorio: texto y acciones a un lado, vista del producto al otro.
Móvil: texto, acciones, nota y una vista compacta del producto, en ese orden.
No reducir una captura de escritorio hasta volver ilegible su contenido.

### Vista del producto

Mostrar una ilustración de la pantalla aprobada de Pesajes: último peso, animal,
hora y unas pocas lecturas recientes. Ejemplos: 437.5 kg, BEDE50D3, Hoy 19:42.
Identificar claramente todo el bloque como Vista de ejemplo. Los valores deben
ser fixtures públicos y estáticos, nunca consultas a stage ni a producción.
No mostrar un estado Conectado que parezca un indicador vivo del home.
Los controles dibujados no deben parecer controles operativos: usar una figura
no interactiva o una demostración explícita, sin botones falsos que reciban foco.

Puede añadirse una fotografía discreta de corral debajo o detrás de una zona sin
texto. Reutilizar recursos existentes. Evitar texto sobre zonas fotográficas con
contraste variable y evitar que la foto desplace el acceso fuera de la portada.

## 6. Cómo funciona — lámina 02

Ancla: #como-funciona.
Título: **Del pesaje al historial, en tres pasos**.

| Paso | Título | Descripción |
|---|---|---|
| 1 | Identifica al animal | El lector reconoce su arete. |
| 2 | Guarda el pesaje | El equipo registra el peso en el corral. |
| 3 | Consulta su historial | Los datos se sincronizan cuando hay conexión. |

Banda verde oscura, texto claro y acentos azules con contraste comprobado.
Usar una lista ordenada; iconos pequeños de apoyo, no como única explicación.
Escritorio: tres columnas. Móvil: tres pasos apilados, sin scroll horizontal.

Reutilizar la idea de `Diagrama.jsx` sustituyendo outbox, nube y éxito de captura
por los textos anteriores. Explicar el flujo sin convertir la página en un
diagrama de arquitectura. No afirmar que el navegador funciona sin internet por
el hecho de que el dispositivo guarde lecturas localmente.

## 7. Beneficios y ejemplo de historial — lámina 02

### En el corral y desde tu celular

Ancla: #beneficios.

| Bloque | Texto |
|---|---|
| Durante el pesaje | Relaciona el animal con su peso en un solo registro. |
| Después de la jornada | Consulta los pesajes y el historial de cada animal. |

Dos bloques breves con imágenes relacionadas con el trabajo real. En escritorio
pueden ir lado a lado; en móvil, apilados. No representar que un teléfono escanea
un arete RFID por sí solo ni que cualquier báscula es compatible. Usar fotos
existentes del corral y una vista ilustrativa del producto antes de crear assets.

### Cada animal tiene su historia

Título: **Cada animal tiene su historia**.
Descripción: **Consulta sus pesajes y sigue cómo cambia su peso con el tiempo.**

Acompañar con una fotografía y una gráfica sencilla de pesos por fecha, con
etiqueta permanente **Ejemplo ilustrativo**. Reutilizar `GraficaPeso.jsx` cuando
sea apropiado, después de revisar sus datos, textos y dependencias. Conservar la
identificación de datos sintéticos; no presentar la serie como un resultado
comercial o como datos reales de un cliente.

La gráfica debe indicar kg y fechas, ser legible en móvil y tener alternativa
textual o tabla accesible. Si la serie contiene una lectura inestable, conservar
su distinción visual y textual. Quitar el texto que promete que el agente guarda
todas las muestras inestables: el agente revisado filtra muestras inestables
antes de crear un evento. No cambiar esa lógica para justificar el marketing.

## 8. Privacidad y preguntas frecuentes — lámina 03

### Bloque de privacidad

Título: **La información de tu rancho, para tu equipo.**
Descripción: **Cada usuario ve únicamente la información que le corresponde.**

Banda breve con icono de candado y texto. No añadir certificaciones, garantías
legales ni explicaciones de consultas, tokens o aislamiento técnico.

### Preguntas frecuentes

Ancla: #preguntas-frecuentes. Título: **Preguntas frecuentes**.

| Pregunta | Respuesta canónica |
|---|---|
| ¿Qué pasa si se va la señal? | El equipo guarda los pesajes localmente y los envía cuando recupera la conexión. Para ver nuevos datos en tu celular necesitas conexión. |
| ¿Cómo entro a Fierro? | El acceso es por invitación. Pide al administrador de tu rancho que dé de alta tu correo y después selecciona Iniciar sesión. |
| ¿Qué información puedo consultar? | Puedes consultar los pesajes y la información de los animales a los que tu cuenta tiene acceso. |
| ¿Qué equipo necesita mi rancho? | Fierro conecta un lector de aretes y una báscula con un equipo que registra los pesajes. La compatibilidad depende de los modelos y debe verificarse antes de instalarlos. |

Acordeón accesible, preferentemente con details/summary nativos. Primera pregunta
abierta por defecto, resto cerradas. Se puede abrir más de una. Toda la cabecera
es pulsable; iconos más/menos decorativos, no controles separados. Mantener foco
visible y funcionamiento con teclado. Evitar animaciones obligatorias o alturas
que recorten respuestas. El texto describe el flujo previsto, no certifica que
las pruebas pendientes de desconexión o compatibilidad física estén completadas.

## 9. Cierre y pie — lámina 03

| Elemento | Texto |
|---|---|
| Título | ¿Tu rancho ya usa Fierro? |
| Descripción | Inicia sesión con tu correo autorizado. |
| Acción | Iniciar sesión |
| Ayuda | Si aún no tienes acceso, pide al administrador de tu rancho que dé de alta tu correo. |

Banda verde oscura con acción azul petróleo y contraste verificado. Móvil:
apilar contenido y botón. No añadir formulario de registro ni contactos ficticios.
Pie con marca original, Del corral a tu bolsillo., Cómo funciona, Preguntas
frecuentes e Iniciar sesión. Los enlaces conservan los destinos anteriores.

## 10. Punto de partida técnico

Leer primero `AGENTS.md` y las guías de [agentes](agent/README.md), en especial
[principios de producto](agent/product-principles.md),
[reglas de ingeniería](agent/engineering-rules.md) y [pruebas](agent/testing.md).
Usar el grafo MCP para descubrimiento de código; recurrir a lectura/búsqueda de
archivos si no devuelve resultados suficientes, como ocurrió en esta revisión.
Verificar el estado actual del repo: esta lista refleja la revisión del 22/09/2026.

| Archivo existente | Papel y precaución |
|---|---|
| ../apps/web/src/Home.jsx | Portada y onEntrar; punto de entrada del cambio. |
| ../apps/web/src/Secciones.jsx | Secciones y aparición al entrar en viewport. Reordenar y simplificar conservando contenido accesible. |
| ../apps/web/src/Shell.jsx | Compartido con login. Evitar cambiarlo globalmente para resolver solo el home. |
| ../apps/web/src/Diagrama.jsx | Base del flujo de tres pasos. |
| ../apps/web/src/GraficaPeso.jsx | Gráfica ilustrativa y alternativa accesible; revisar antes de reutilizar. |
| ../apps/web/src/Foto.jsx | Fotos y créditos; preservar atribuciones. |
| ../apps/web/src/Marca.jsx | Marca canónica; no reemplazarla por dibujos generados. |
| ../apps/web/src/styles.css | Estilos compartidos. Acotar reglas del home. |

Revisar `apps/web/src/img` y `apps/web/public/img` antes de agregar fotografías.
No importar rutas de la carpeta personal .codex/generated_images en código.
Las láminas versionadas son referencias, no assets que deban cargarse en el sitio.

## 11. Secuencia de implementación sugerida

1. Revisar estado Git, instrucciones y componentes actuales; trabajar en una rama
   feature. No incluir worktrees, capturas RFID ni imágenes sueltas ajenas al cambio.
2. Crear contenedor y tokens del home, manteniendo intactas las otras pantallas.
3. Implementar encabezado y portada con la marca y onEntrar existentes.
4. Crear la vista ilustrativa con datos fijos identificados como ejemplo.
5. Reorganizar pasos, beneficios e historial reutilizando componentes y fotos.
6. Añadir preguntas frecuentes, privacidad, cierre y pie.
7. Externalizar textos por claves traducibles según la guía de producto; usar el
   mecanismo existente si lo hay. No emprender una migración global de idiomas.
8. Revisar escritorio y móvil con contenido completo; ajustar jerarquía y espacios.
9. Ejecutar las comprobaciones siguientes y documentar evidencia de la versión final.

## 12. Validación y criterios de aceptación

- [ ] Marca, paleta verde/marfil/azul petróleo y etiquetas consistentes en toda la página.
- [ ] Sin acentos café/dorado en la interfaz del home.
- [ ] Un único H1, encabezados jerárquicos y contenido principal en main.
- [ ] Iniciar sesión visible y funcional; todos sus botones usan el flujo existente.
- [ ] Anclas funcionales y no ocultas bajo un encabezado fijo.
- [ ] Ejemplos claramente identificados, sin consultas públicas a datos privados.
- [ ] Ningún control ficticio, registro público, métrica o promesa inventada.
- [ ] Fotografías existentes reutilizadas cuando encajen y créditos preservados.
- [ ] Sin scroll horizontal de página a 375, 390, 768 y 1440 px.
- [ ] Vista del producto y gráfica legibles; en móvil no son capturas diminutas.
- [ ] Controles táctiles de al menos 44 × 44 px, foco visible y navegación por teclado.
- [ ] Estados abiertos/cerrados de FAQ accesibles; información no dependiente del color.
- [ ] Movimiento reducido respetado; animaciones no dejan secciones ocultas si fallan.
- [ ] Imágenes dimensionadas para evitar saltos; carga diferida debajo de la portada.
- [ ] Login, dashboard y administración mantienen su apariencia y funcionamiento.
- [ ] pnpm lint y pnpm build pasan desde apps/web.
- [ ] Capturas finales de escritorio y móvil y revisión manual de enlaces/FAQ/login.

No agregar tests que solo repliquen el marcado. Aplicar las comprobaciones de
[testing](agent/testing.md) apropiadas al código efectivamente modificado.
No desplegar ni promover ramas de entorno como parte de este rediseño.

## 13. Entrega esperada del siguiente modelo

Entregar el frontend implementado, resumen de archivos modificados, validaciones
realmente ejecutadas, capturas de escritorio/móvil y limitaciones concretas.
Actualizar esta guía si se acuerda un cambio de alcance o texto. No presentar los
mockups como evidencia de que la interfaz ya existe o de que las pruebas de
hardware, recuperación offline y permisos pendientes ya se completaron.
