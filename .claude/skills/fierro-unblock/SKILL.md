---
name: fierro-unblock
description: "What to do when development stalls in Fierro IoT: timebox thresholds, the alternatives ladder (narrow scope, loud stub, alternative path, timeboxed spike, escalate), what is forbidden while stuck, and the escalation template. Use when blocked, when the same error repeats, when hardware or a decision is missing, or when tempted to fake data to make a test pass."
---

# Fierro unblock protocol

Full guide: [`docs/agent/unblock.md`](../../../docs/agent/unblock.md)

## When to use

- The same error repeats after different attempts
- A driver, protocol, credential, decision, or piece of hardware is missing
- The approach is not converging and time keeps going
- You are about to disable a test, fake data, or swallow an exception

## Central rule

> **Retrying in silence is the worst possible outcome.**
> Change strategy or deliver an alternative. Never keep hammering the same approach.

## Stall thresholds

| Signal | Threshold |
|---|---|
| Same error after different attempts | **3 attempts** |
| One sub-problem with no measurable progress | **~45 min** |
| Something needed is unavailable (hardware, credential, manual, decision) | Immediate |
| Fix would change a contract or unagreed infra | Immediate |
| Tests only pass by disabling or faking something | Immediate |

## The alternatives ladder

1. **Narrow to a vertical slice.** Ship the thinnest end-to-end version, ticket the rest
2. **Loud stub behind the interface.** `raise NotImplementedError("...")` with a linked ticket. Never fake a value
3. **Alternative path.** Unknown indicator protocol → capture raw bytes. No scale → virtual serial and fixtures. No LTE → develop over Wi-Fi. MQTT unavailable → HTTP batch already works
4. **Timeboxed Spike ticket.** Concrete question, explicit timebox, exit criterion is a written recommendation
5. **Escalate to the user.** Only for decisions or resources the agent cannot obtain. Deliver everything that did not depend on the answer first

## Forbidden while stuck

- Silently fake data to make a test pass
- Empty `try/except` to hide the symptom
- Disabling or deleting tests that get in the way
- Rewriting half the repo because the first approach failed
- Changing the data contract without a ticket and migration
- Reporting as finished something left half-done

## Escalation template

Always include all five parts: **Blocker**, **What was tried** (numbered, with results),
**Root cause or hypothesis**, **Options** (table with cost, risk, reversible), **Recommendation**
(one option with reasoning), and **Delivered meanwhile** (what does work and is tested).

## Always escalate these

Scale, indicator or RFID reader brand and model. Country, LTE carrier and bands.
Any change to the data contract. Migrating to Postgres or MQTT. Fleet identity scheme.
Fabricating a PCB revision. Multi-tenant vs single ranch.

## Related

- [`fierro-engineering-rules`](../fierro-engineering-rules/SKILL.md) — reversible vs one-way decisions
- [`fierro-sprints`](../fierro-sprints/SKILL.md) — spikes and planning
- [`fierro-jira`](../fierro-jira/SKILL.md) — ticket templates
