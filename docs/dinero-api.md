# Captura de dinero — etapa 1 (#173)

La migración 014 agrega un ledger por organización. 012 y 013 quedan reservadas
para búsqueda y adjuntos. La especificación usada es el cuerpo de #173 y la épica
#123; `docs/finanzas/modelo-dinero.md`, citado por el issue, no existe en la base
actual. Los cálculos y la pantalla corresponden a #174 y #175.

## Reglas del contrato

- UUID generado por el cliente; mismo UUID y contenido devuelve lo guardado.
  Otro contenido u otro autor con esa clave devuelve 409.
- Montos y precios positivos con hasta dos decimales; la respuesta los expresa
  como cadenas para conservar centavos exactos. No se redondea una entrada de
  tres decimales. No se recibe organización, autor ni estado en el JSON.
- Compra y venta requieren un animal ya registrado. Gasto requiere categoría
  y alcance animales (uno o varios), corral (etiqueta libre) o hato. Un periodo
  de gasto requiere ambas fechas y fin igual o posterior al inicio.
- Registrar otra compra de un animal con compra vigente devuelve 409, y lo mismo
  otra venta con venta vigente. Una venta con fecha anterior a la compra vigente,
  o una compra con fecha posterior a la venta vigente, también devuelve 409; la
  misma fecha es válida. Se excluyen originales anulados y filas de anulación. Sin compra
  vigente, la venta sigue permitida. Los reintentos con el mismo UUID y contenido
  conservan su comportamiento idempotente.
- Precio de mercado se registra a nivel hato, sin animales, monto ni categoría.
  El precio vigente es el más reciente por fecha de evento hasta hoy UTC; los
  empates se resuelven por registro y UUID. Sin uno vigente devuelve `null`.
- `source_entry_id` es opcional y debe pertenecer a la organización de sesión.
  Las relaciones de animales y fuente también se protegen con FKs compuestas.
- `desde` y `hasta` son fechas inclusivas. `estado=vigente` es el filtro por
  defecto. `anulado` muestra originales anulados, `anulacion` sus reversos y
  `todos` el ledger completo, incluyendo historial de precios futuros/anulados.
- La anulación pide su propio UUID y fecha. Inserta una fila con los datos del
  original y `voids_movement_id`. La vista deriva `estado=anulado` para el
  original. Su `status` guardado permanece `confirmado`; ninguna fila se edita.
  Una anulación no vuelve a anularse, ni un original puede anularse dos veces.
- Usuarios normales usan siempre su organización; el superusuario requiere
  `?org=<slug>` explícito. La aplicación no expone UPDATE ni DELETE. La migración
  documenta los permisos del rol SQL de ejecución.

## Ejemplos locales

Aplicar primero `fierro-api-migrate`. Reemplazar UUID y arete por los del entorno
de prueba. Para superusuario agregar `?org=<slug>` a cada URL.

```bash
curl -H "Authorization: Bearer $FIERRO_KEY" -H 'Content-Type: application/json' \
  http://localhost:8000/v1/dinero/movimientos -d '{
    "movement_id":"b3834962-a787-42f7-a2e8-39d1234cab47",
    "kind":"compra","amount_mxn":"12450.50","weight_kg":"365.20",
    "occurred_on":"2026-11-18","scope":"animales","animals":["MX-0182"]}'

curl -H "Authorization: Bearer $FIERRO_KEY" \
  'http://localhost:8000/v1/dinero/movimientos?animal=MX-0182&desde=2026-11-01&hasta=2026-11-30&estado=vigente'

curl -H "Authorization: Bearer $FIERRO_KEY" -H 'Content-Type: application/json' \
  http://localhost:8000/v1/dinero/movimientos/b3834962-a787-42f7-a2e8-39d1234cab47/anular \
  -d '{"movement_id":"42ae09a3-2a5d-488d-a144-46ece6140765","occurred_on":"2026-11-18"}'

curl -H "Authorization: Bearer $FIERRO_KEY" http://localhost:8000/v1/dinero/precio
```
