# Foto de animal con extensión incorrecta

2026-09-27. Corrección local en `codex/stage-shared-access`, sin publicar.

El archivo reportado tiene firma JPEG (`FF D8 FF`) pero extensión PNG. La
optimización de imágenes pequeñas devolvía el archivo original con MIME inferido
de la extensión; la API rechazaba la discrepancia correctamente.

`photo.js` reconoce ahora la firma JPEG, PNG o WebP antes de las rutas de retorno
temprano y normaliza el nombre y MIME sin cambiar los bytes. La validación de la
API permanece intacta; reconocer una firma no sustituye validar el archivo.

Verificación: seis pruebas Node pasan (foto y lecturas), ESLint y build pasan.
El archivo real de 8955 bytes se procesó localmente: salida JPEG con bytes
idénticos. No se subió la imagen ni se reemplazó una foto en stage como parte
de la prueba. Falta publicar y comprobar el flujo completo en navegador.
