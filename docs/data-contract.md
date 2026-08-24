# Contrato de datos — pesaje

## Evento de pesaje (`WeightReading`)

```json
{
  "event_id": "0192f0a0-7c3d-7b2a-9c1e-5f6a7b8c9d0e",
  "device_id": "rpi-ranch-001",
  "tag_id": "982000123456789",
  "weight_kg": 412.5,
  "captured_at": "2026-08-24T00:15:30.123456+00:00",
  "stable": true,
  "source": "mock"
}
```

| Campo | Tipo | Notas |
|-------|------|-------|
| `event_id` | UUID string | Idempotencia global; generado en edge |
| `device_id` | string | Identidad del RPi / estación |
| `tag_id` | string | ID ISO11784 decodificado del arete |
| `weight_kg` | float | Peso estable en kg |
| `captured_at` | ISO-8601 UTC | Momento de la asociación RFID+peso |
| `stable` | bool | true si pasó filtro de estabilidad |
| `source` | string | `mock` \| `serial` \| etc. |

## Heartbeat de device

```json
{
  "device_id": "rpi-ranch-001",
  "sent_at": "2026-08-24T00:16:00+00:00",
  "pending_count": 3,
  "agent_version": "0.1.0",
  "uptime_s": 3600
}
```

## Endpoints MVP

- `POST /v1/readings` — body: un evento o `{ "readings": [...] }`; responde 200 aunque sea duplicado
- `GET /v1/readings?limit=50` — listado reciente
- `POST /v1/devices/{device_id}/heartbeat`
- `GET /v1/devices` — estado de devices
- `GET /health`
