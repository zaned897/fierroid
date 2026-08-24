---
name: fierro-edge-reliability
description: "Keep the Raspberry Pi alive in the field: power-loss safety, SD card corruption, SQLite durability, watchdogs, RTC and clock trust, disk-full policy, thermal limits, and safe OTA. Use when touching the device agent, outbox storage, systemd units, deployment, or device reliability."
---

# Fierro edge reliability

Full guide: [`docs/agent/edge-reliability.md`](../../../docs/agent/edge-reliability.md)

## When to use

- Changing capture, outbox, sync, or storage in `apps/device-agent`
- Anything about power, boot, systemd, SD cards, or OTA updates
- Designing how the device behaves when something fails
- Reviewing whether a change survives a blackout

## Base rule

> **Design assuming power cuts at the worst possible instant.**
> In a ranch the blackout is not the edge case, it is the normal case.

## Top failure modes and mitigations

| Threat | Mitigation |
|---|---|
| Power cut mid-write | UPS that **signals** the loss over GPIO, triggering ordered shutdown (30 s budget) |
| SD corruption and wear | Read-only root with overlayfs, separate data partition, `noatime`, volatile journald, **industrial SD or eMMC** |
| Losing committed readings | `PRAGMA synchronous=FULL` on the capture path. `NORMAL` plus WAL can lose recent commits on power loss |
| Pi has no RTC | Battery-backed RTC on the custom PCB, chrony over LTE, `clock_synced` flag, server-side `received_at` |
| Process hung (serial blocked) | Hardware watchdog plus systemd `WatchdogSec` and `sd_notify`; timeouts on every serial read |
| Disk full after weeks offline | `pending_count` and disk percent in heartbeat, early alarm, **never delete `pending` without ACK** |
| Sealed enclosure in the sun | Conducted cooling to the chassis, SoC temperature and throttling in heartbeat |
| Bad OTA across the fleet | A/B with auto-rollback (RAUC, Mender, SWUpdate), staged canary, data partition untouched |

## Systemd expectations

`Restart=always`, `RestartSec=5`, `StartLimitIntervalSec=0`, `WatchdogSec` with `sd_notify`,
`MemoryMax`, and `RuntimeWatchdogSec` enabled system-wide.

## Required chaos tests

Any change to capture, outbox, or sync must pass:

- Power cut during write, repeated → 0 confirmed readings lost, DB intact
- `kill -9` mid-weighing → clean restart, `pending` intact
- LTE down and restored → no duplicates, backoff with jitter
- Data partition full → loud failure and alert, no `pending` deletion
- Clock jump backwards or forwards → intervals unaffected, timestamps flagged
- System reboot → service starts on its own and drains the queue

Use `FIERRO_MOCK_HW=1` when there is no hardware.

## Related

- [`fierro-engineering-rules`](../fierro-engineering-rules/SKILL.md) — pillars and standards
- [`fierro-hardware-boundary`](../fierro-hardware-boundary/SKILL.md) — electrical protection and PCB
