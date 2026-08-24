---
name: fierro-engineering-rules
description: "Core engineering rules for Fierro IoT: pragmatism, robustness, scalability to thousands of stations, and industrial standards (ISO 11784/11785, OIML R76, IPC, MQTT/Sparkplug). Use before any non-trivial design decision or implementation in device-agent, api, or web."
---

# Fierro engineering rules

Full guide: [`docs/agent/engineering-rules.md`](../../../docs/agent/engineering-rules.md)

## When to use

- Before implementing any non-trivial change
- Choosing between approaches, libraries, or protocols
- Reviewing whether a change is safe for a fleet of thousands
- Anytime you are about to invent something a standard already solves

## Root invariant

> **No weight reading is ever lost.** Everything else is negotiable.

If a change risks this, it does not ship, even if the ticket asks for it.

## The 5 pillars

| Pillar | Rule |
|---|---|
| **Pragmatism** | Simplest solution that survives the corral. Boring tech by default. Buy, don't build |
| **Robustness** | Fail loudly, never fake data. Assume `SIGKILL` between any two instructions |
| **Scalability** | Autonomous devices, stateless API, retry backoff **plus jitter**, per-device identity from day 1 |
| **Industrial standards** | Existing norm beats custom invention |
| **HW/SW separation** | Software knows no baud rates. See `fierro-hardware-boundary` |

## Hard rules that catch most mistakes

1. **Minimal diff.** Out-of-scope refactor is a separate ticket
2. **Idempotency** on anything crossing the network (`event_id`)
3. **Nothing marked `synced` without server ACK**
4. **Jitter in retries.** Thousands of devices reconnect the same second when LTE returns
5. **YAGNI, except at boundaries** (hardware drivers, sync transport, cloud persistence)
6. **One-way doors** (data contract, device identity, fabricated PCB rev) need user approval

## Key standards

ISO 11784/11785 (animal RFID), ISO 24631 (reader conformance), OIML R76 (non-automatic
weighing), TIA/EIA-232-F and -485-A (serial), Modbus RTU, MQTT + Sparkplug B, IEC 62443
(OT security), IEC 60529 / NEMA 4X (enclosure), IEC 61000-4 (EMC), IPC-2221/2152/7351/A-610
(PCB), ISO 8601 UTC, UUID v7 (RFC 9562), SemVer 2.0.0.

## PR checklist

- [ ] Can this lose a reading? Why not?
- [ ] What happens if power cuts mid-operation?
- [ ] What happens at 5,000 devices at once?
- [ ] Does an industrial standard already solve this?
- [ ] Did the diff stay inside the ticket scope?

## Related

- [`fierro-edge-reliability`](../fierro-edge-reliability/SKILL.md) — field survival
- [`fierro-hardware-boundary`](../fierro-hardware-boundary/SKILL.md) — HW/SW split, PCBs
- [`fierro-unblock`](../fierro-unblock/SKILL.md) — when development stalls
- [`fierro-sprints`](../fierro-sprints/SKILL.md) — tickets and sprints
