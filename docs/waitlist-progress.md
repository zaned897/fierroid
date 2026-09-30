# Lista de espera temporal

Unidad: formulario público en home y consulta exclusiva de superusuarios.
Supuesto inicial: lista de espera sin pago, sin reserva de equipo ni fecha de entrega.
Campos: nombre, correo, estaciones estimadas y consentimiento de contacto.
Persistencia PostgreSQL separada de usuarios; correo único y reintentos sin duplicados.
Los reenvíos no sobrescriben datos de otra persona. Respuesta pública sin revelar si
el correo ya existía. Límite global de 100 altas por hora como contención inicial,
campo trampa y validación en servidor. No envía emails ni habilita acceso al panel.
Pruebas previstas: persistencia, duplicados, validación, permisos y UI local.
No desplegar esta unidad hasta revisión; la guía anterior del home que excluía
registro público queda ampliada únicamente para este formulario de interés.

Implementado y probado localmente (2026-09-29): 197 pruebas Python aprobadas,
Ruff, mypy y lint/build web. Navegador: envío de formulario confirmado por API;
anchos 375, 390, 768 y 1440 sin desbordamiento horizontal. Consulta administrativa
verificada por API (401 sin sesión, 403 usuario normal, lectura superusuario).
Migración 008 aplicada solo a PostgreSQL local. Pendiente revisión de producto y
publicación. No hay confirmación por correo ni verificación de propiedad del email;
los registros son expresiones de interés, no identidades verificadas.
