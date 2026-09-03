---
name: fierro-product-principles
description: "How Fierro is built beyond the engineering rules: elegance over state-of-the-art, multi-language from day one, staged end-to-end releases (v1, v2, v3), root-cause debugging with no patches, simple minimal field-ready design, and Raspberry Pi / Sixfab / LoRaWAN compatibility. Load before writing code, adding a field to the data contract, adding UI text, or fixing a bug."
---

# Fierro product principles

Full guide: [`docs/agent/product-principles.md`](../../../docs/agent/product-principles.md)

## When to use

- Before writing code on any app in this repo
- Adding user-visible text, or any UI at all
- Adding a field to the data contract
- Fixing a bug
- Deciding whether something is ready to release

Complements [`fierro-engineering-rules`](../fierro-engineering-rules/SKILL.md); it does not replace it.

## 1. Elegance beats state-of-the-art

Simplest solution that solves the real problem wins. We do not build to show
sophistication. Elegant here means **little code, obvious to read, hard to misuse** —
not clever.

Delete an abstraction that has one implementation. Reject a pattern nobody can
explain in two minutes.

## 2. Multi-language by design

Spanish first, English second, a third one without rewriting.

| Layer | Language |
|---|---|
| Code identifiers | English |
| Comments and docs | Spanish |
| **User-visible text** | **translatable, never inline** |
| Data and event contract | neutral (ISO-8601 UTC, kg) |

Never concatenate sentences. Never store formatted dates. Codes like `pending`
and `stable` are contract values, not text — translate them at render time.

## 3. Ship in stages: v1, v2, v3

A version is a **vertical end-to-end MVP**, never a finished layer. It ships when
a real weight reading travels ear tag → scale → RPi → cloud → PWA and someone can
use it. SemVer; a `vX.Y.Z` tag marks a closed, deployable stage.

Sprints are the cadence, versions are the deliverable. They need not coincide.

## 4. Tests always

See [`docs/agent/testing.md`](../../../docs/agent/testing.md). A bug closes with a test that
**failed before** the fix. A test that only passes under ideal conditions —
empty database, perfect network — is testing nothing.

## 5. Root cause, never patches

> If you do not know **why** it fails, you cannot fix it yet.

Reproduce → confirm the cause through two independent paths → write a failing
test → fix the cause → test passes.

**Forbidden:** swallowing `try/except`, an extra `if` for the failing case,
retry-until-green, raising a timeout, or adjusting the test so it passes. Each
one hides the failure instead of removing it.

Still uncertain after investigating? That is being stuck: use
[`fierro-unblock`](../fierro-unblock/SKILL.md). A loud stub with an open ticket is honest;
a patch that "seems to fix it" is not.

## 6. Simple, modern, minimal design

The PWA is used in the corral: direct sun, gloves, one hand, poor signal.

One hero datum per screen (the weight). Mobile-first at 375px. High contrast.
Touch targets 44×44px minimum. No decorative shadows or gratuitous animation.
Empty states teach. Errors are shown, never hidden — an unstable reading is
flagged, not dropped.

## 7. Hardware and transport compatibility

Target: Raspberry Pi, Sixfab / LTE, **and** LoRa / LoRaWAN.

The current JSON event is **205 bytes**. LoRaWAN budgets: ~11 bytes (US915 DR0),
~51 bytes (EU868 DR0). **It does not fit.** A binary encoding of the same event
is ~17 bytes — and in it, `device_id` becomes the DevEUI and `event_id` is
derived from `DevEUI + counter` instead of a random UUID.

> **Before adding a field to the event contract, ask whether it fits in 17 bytes.**
> If it does not, decide explicitly that it travels over LTE only, and write down why.

The data contract is a one-way door. Widening it without considering the
narrowest link is the easiest way to lose LoRaWAN without noticing.

LoRaWAN is a stated goal, **not an approved design**. Primary vs fallback,
public network vs own gateway, and regional band are all undecided — those need
a Spike and a user decision, not code.

## Related

- [`fierro-engineering-rules`](../fierro-engineering-rules/SKILL.md) — pillars and standards
- [`fierro-hardware-boundary`](../fierro-hardware-boundary/SKILL.md) — HW/SW split and drivers
- [`fierro-edge-reliability`](../fierro-edge-reliability/SKILL.md) — field survival
- [`fierro-unblock`](../fierro-unblock/SKILL.md) — when the root cause will not appear
- [`fierro-sprints`](../fierro-sprints/SKILL.md) — tickets, DoR / DoD
