---
name: fierro-sprints
description: "How work is organized in Fierro IoT: sprint cadence and goals, work hierarchy including timeboxed Spikes, ticket granularity, Definition of Ready and Definition of Done, and technical debt tracking. Use when planning, breaking down work, writing or picking up a ticket, or deciding whether something is ready to close."
---

# Fierro sprints and tickets

Full guide: [`docs/agent/sprints.md`](../../../docs/agent/sprints.md)

## When to use

- Planning or breaking down work
- Writing, picking up, or closing a ticket
- Deciding whether something is ready to start or ready to close
- Judging whether a request belongs to this sprint or a later one

## Central rule

> **All non-trivial work starts as a ticket and ends in a linked PR.**
> One ticket, one branch, one PR.

## Cadence

- **2-week sprints** (1 week acceptable during prototyping)
- **One sprint goal**, written as an observable outcome, not a task list
- Roadmap lives in the [README](../../../README.md), living backlog lives in Jira

## Work hierarchy

**Epic** (sprint theme) → **Story** (user value) → **Task** (technical work) →
**Bug** (with repro) → **Spike** (timeboxed investigation).

Spike is first-class here: most risk in this project is unknown hardware.

## Granularity

1. One ticket is **2 days of work or less**, otherwise split it
2. Split into **vertical slices, not layers**
3. **Hardware and software never share a ticket** — different lead time and risk
4. Hardware tickets carry **explicit lead time**; plan them one sprint ahead
5. Labels: `edge`, `api`, `web`, `hardware`, `pcb`, `infra`, `docs`, `deuda`

## Definition of Ready

Context, scope **and** out-of-scope, measurable acceptance criteria, affected apps,
identified dependencies, and an evaluated risk to the root invariant
("can this lose a reading?"). If something is missing, ask the user or make it a Spike. Never guess.

## Definition of Done

- [ ] Acceptance criteria met, one by one
- [ ] `ruff check apps` and `pytest apps/device-agent apps/api -q` green
- [ ] `pnpm lint && pnpm build` if `apps/web` was touched
- [ ] Evidence in the PR (test output, screenshot, curl)
- [ ] Outbox and idempotency invariants intact
- [ ] Chaos tests run if capture or sync was touched
- [ ] Docs updated if behavior or convention changed
- [ ] PR linked to the ticket, ticket moved
- [ ] Any stub left behind has an open, visible ticket

Never mark Done with failing, disabled, or "should work" tests.

## Agent rules inside a sprint

Do not widen ticket scope mid-flight (findings become new tickets). Do not pull work from
future sprints (Postgres, MQTT, OTA) unless asked. Report blockers during the sprint, not at
the end. Deliver everything that was not blocked and say explicitly what was left out and why.
Any finding that risks the root invariant always becomes a ticket.

## Related

- [`fierro-jira`](../fierro-jira/SKILL.md) — templates and Atlassian MCP
- [`fierro-pull-requests`](../fierro-pull-requests/SKILL.md) — branches and PRs
- [`fierro-unblock`](../fierro-unblock/SKILL.md) — blockers and spikes
