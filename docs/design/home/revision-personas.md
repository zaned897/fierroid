# Revisión de personas — primera entrega

2026-11-12 · Revisión visual de los archivos en `apps/web/public/img/`, no solo de sus prompts. Las decisiones son propuestas para el lote posterior: ningún original se reemplaza aquí. «Se queda» significa que puede conservarse; «se regenera» indica el cambio recomendado al aplicar conjuntamente #155 y #156.

| Archivo actual | Decisión | Evidencia visual y motivo |
|---|---|---|
| `home-corral-ia.webp` | Se regenera | Trabajador de espaldas observando un cebú desde fuera de la manga; no posa ni mira a cámara. Cumple postura, pero gorra/ropa bastante limpias y fondo de pradera arbolada verde no fijan el entorno semiárido de #155. Conservar la acción. |
| `home-corral-v2-ia.webp` | Se queda | Vista por detrás del hombro, mirada al celular, camisa arrugada y sombrero usado; tubos con desgaste, bovino negro y luz de día. Pantalla sin contenido legible; no apunta al arete. No requiere regeneración por personas. |
| `home-consulta-ia.webp` | Se regenera | Persona sentada y vista desde atrás, concentrada en el teléfono; postura válida. El césped y arbolado verde del fondo se apartan del paisaje acordado; trasladar la consulta a sombra de rancho semiárido y acentuar uso cotidiano de la ropa. |
| `mqb-equipo-ia.webp` | Se regenera | Espalda, sombrero usado y consulta al celular cumplen #156. Sol en horizonte y cielo naranja dominan la escena; cambiar a día neutro y corral de tubo/tabla. Muestra v3 entregada, sin sustituir original. |
| `mqb-comprador-ia.webp` | Se regenera | Dos personas por detrás, sin contacto con cámara. Contraluz dorado, sierra dramática y estilización de vestuario dan aspecto de catálogo. Muestra v3 con personas sentadas trabajando y luz diurna. |
| `seccion-arete.webp` | Se regenera | Persona mayor realmente ocupada en manejo, ropa usada, sin mirar a cámara; el perfil es cercano, no lejano. Reencuadrar por detrás o a distancia y evitar marcas/texto del equipo. Es fotografía acreditada, no un fallo de generación. |
| `seccion-hato.webp` | Se regenera | Jinete sentado entre ganado, cabeza girada hacia el observador; no se puede certificar la dirección de los ojos a esta resolución. Camisa con letras y manga corta, entorno exuberante. Sustituir por trabajo de espaldas en paisaje semiárido; créditos identifican la foto como Pantanal, Brasil. |
| `seccion-manga.webp` | Se regenera | Personas trabajando de frente y perfil cercano, incluidas personas menores; no hay sonrisa posada evidente, pero el encuadre no cumple espaldas/perfil lejano/sentadas. Preferir adultos de espaldas y manejo visto a distancia; no reproducir la escena como testimonio de Fierro. |
| `home-hero.webp` | Se regenera | Inspeccionada: no contiene personas, solo un cebú bajo árboles. Vegetación tropical muy verde; renovación por #155, no por postura. La portada v3 es candidata común para esta y `home-paisaje-ia`. |
| `seccion-corral.webp` | Se queda | Inspeccionada: sin personas visibles; ganado y cercas, sin incumplimiento de #156. Su tratamiento histórico puede revisarse al armonizar el lote de #155. |

Los PNG `home-corral-ia.png` y `home-consulta-ia.png` se revisan también como originales de sus WebP; comparten escena y decisión. No se deduce que una persona sea modelo por su apariencia: se evalúan postura, mirada, vestuario y contexto visibles. Los recursos `seccion-*` y `home-hero` son fotografías previas según `CREDITOS.md`.

## Muestras v3

Las tres muestran campo seco, corrales usados y luz diurna de tratamiento neutro. Equipo: una persona de espaldas consultando el celular. Comprador: dos personas sentadas en la camioneta mirando el teléfono, sin posar. Las pantallas se alcanzan a ver de oblicuo, pero no contienen información legible; si se exige ocultarlas por completo, ajustar ese punto en la próxima iteración. No se aprecian deformaciones evidentes a tamaño de revisión; el ganado parcialmente oculto por cercas exige nueva revisión al elegir recortes finales. Pendientes de aprobación visual e integración; estas muestras no cierran los issues.
