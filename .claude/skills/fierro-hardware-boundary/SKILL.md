---
name: fierro-hardware-boundary
description: "Keep hardware and software separated in Fierro IoT: the HardwareBackend HAL contract, per-brand serial drivers, testing drivers without hardware via golden captures and HIL, the hardware/ repo layout, hardware revisions vs SemVer, and when a custom PCB is justified. Use for serial drivers, RFID or scale integration, PCB, enclosure, or BOM work."
---

# Fierro hardware boundary

Full guide: [`docs/agent/hardware-boundary.md`](../../../docs/agent/hardware-boundary.md)

## When to use

- Writing or changing a scale or RFID serial driver
- Any task mentioning PCB, enclosure, wiring, connectors, or BOM
- Deciding which side of the boundary a piece of logic belongs on
- Testing hardware-dependent code without hardware

## The contract

> **Software knows no baud rates. Hardware knows no business logic.**

The boundary already exists: the `HardwareBackend` Protocol in
[`hardware.py`](../../../apps/device-agent/src/fierro_device/hardware.py).

1. Baud rates, framing, checksums, GPIO pins live **inside the driver only**. `main.py` never imports `pyserial`
2. The driver returns a raw sample. It does not validate business rules, generate `event_id`, or talk to the cloud
3. One driver per brand and model, selected by env var (`FIERRO_SCALE_DRIVER=...`)
4. A PR that changes both a driver **and** `main.py` means the boundary is in the wrong place
5. No hardware means failing loudly (`NotImplementedError`), never faking a weight

## Testing without hardware

- **Golden captures:** record real serial traffic into fixtures, replay them in tests
- Dirty cases are required: partial frame, noise, unstable weight, negative value, pounds, two tags in a row
- Virtual serial (`socat` or pty) for local integration
- **HIL bench:** one Pi wired to real gear, the only place `FIERRO_MOCK_HW=0` runs outside the ranch
- CI and Cloud Agents always use `FIERRO_MOCK_HW=1`

## Repo separation

Hardware does **not** live in `apps/`:

```
hardware/carrier-board/   # KiCad schematic and PCB, per revision
hardware/enclosure/       # mechanical
hardware/bom/             # part numbers and suppliers
hardware/test-fixtures/   # real serial captures
```

Versioning: software uses **SemVer**, hardware uses a **revision** (`rev-B`).
The device reports both (`agent_version` and `hw_rev`) in the heartbeat.

## Custom PCB, when

| Stage | Use |
|---|---|
| Sprint 0 to 1 | Commercial HATs and wiring. **No custom PCB** |
| Validated in field for at least one sprint | Custom PCB if wiring is the actual problem |
| Production | Own carrier board, ideally CM4 or CM5, controlled revision and BOM |

A fabricated PCB is a **one-way door** and needs user approval. It exists to solve:
power input protection, integrated UPS with power-loss signal, **battery-backed RTC**,
galvanically isolated serial, line TVS, keyed connectors, diagnostic LEDs.

Design against **IPC-2221, IPC-2152, IPC-7351, IPC-A-610**. Commit sources, not just gerbers.

## Related

- [`fierro-edge-reliability`](../fierro-edge-reliability/SKILL.md) — power and field survival
- [`fierro-sprints`](../fierro-sprints/SKILL.md) — hardware tickets carry lead time
