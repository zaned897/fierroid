# Device agent (Raspberry Pi)

Captures RFID + stable weight, writes to SQLite outbox first, then syncs to the API.

```bash
FIERRO_MOCK_HW=1 FIERRO_API_URL=http://127.0.0.1:8000 fierro-device
```
