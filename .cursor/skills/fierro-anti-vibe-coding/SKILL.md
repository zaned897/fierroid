---
name: fierro-anti-vibe-coding
description: "Guardrails against vibe coding in Fierro IoT: query the indexed code graph before writing anything, treat the versioned OpenAPI contract and SQL migrations as the source of truth, work atomically with a passing test, and stop after three failed attempts. Load before writing any new function, adding an endpoint or a database field, or when the same error repeats."
---

# Fierro: anti vibe coding

Full guide: [`docs/agent/anti-vibe-coding.md`](../../../docs/agent/anti-vibe-coding.md)

## When to use

- **Before writing any new function** — it may already exist
- Adding an endpoint, a response field, or a database column
- When the same error survives two attempts
- Before proposing a rule or convention — it is probably already written

## 1. Search the graph before writing

This repo is indexed in a queryable code graph (`codebase-memory`). Querying it
is **not optional** before writing new code.

| Question | Tool |
|---|---|
| Does this already exist? | `search_graph(query="verify password")` |
| Where is `X` defined? | `search_graph(name_pattern="upsert_.*")` |
| Who calls this, what breaks? | `trace_path(function_name="...", mode="calls")` |
| How is the system shaped? | `get_architecture(aspects=["all"])` |

Searching costs seconds. Duplicating a function costs the rest of the project:
two copies of the same logic, one gets fixed and the other does not.

A stale index lies confidently, which is worse than no index. `detect_changes`
shows drift; `index_repository` refreshes it.

## 2. The contract is a file, not a consequence

`docs/contracts/openapi.json` is versioned. Changing the API surface requires
updating it in the same commit, and `test_contract.py` fails otherwise.

```bash
python -m fierro_api.contract           # regenerate after a deliberate change
python -m fierro_api.contract --check   # verify
```

For anything that persists data the order is **SQL migration → test → logic**,
never the reverse. **Never invent a field** that is not in the contract or a
migration. Schemas are one-way doors; logic is rewritten in an afternoon.

## 3. Atomic, with a passing test

One function, one test, green. **Do not move to the next module while the
current one is red** — a carried-over failure becomes three failures and nobody
knows which caused which.

Three attempts on the same error is not a generation problem, it is being
stuck: use [`fierro-unblock`](../fierro-unblock/SKILL.md).

Regenerating without understanding the error is the most expensive way to fix
nothing. Reproduce, confirm the cause two ways, write the failing test, fix the
cause. See [`fierro-product-principles`](../fierro-product-principles/SKILL.md).

## 4. If you cannot explain it, it does not ship

Two minutes, out loud, why the change is correct. Applies equally to code an
agent wrote.

| Gate | When | Catches |
|---|---|---|
| `pre-commit` | before commit | style, stale contract, unsynced skills |
| CI | on the PR | ruff, pytest against real Postgres, web build, compose smoke |
| Human review | before merge | whether it is the right solution at all |

The first two cannot be skipped. `/code-review` gives an independent audit
before opening the PR, useful precisely because it arrives without the author's
context.

## 5. File size

The usual "max 100–200 lines" does not apply here: `main.py` and `auth.py`
exceed 400, and splitting by line count would make them worse. The real
criterion is cohesion — one file, one subject. Past ~400 lines, ask whether two
subjects got mixed; do not split mechanically. What is meant to be replaced
later lives apart, which is why photos have their own module and table.

## Checklist

- [ ] Did I search the graph for this?
- [ ] Did I load the skill covering what I am touching?
- [ ] If it persists data: migration and contract first?
- [ ] Do I know which test proves it works?
- [ ] Can I explain in two minutes why it is correct?
- [ ] Is this inside the ticket, or am I expanding it?

## Related

- [`fierro-product-principles`](../fierro-product-principles/SKILL.md) — how we build here
- [`fierro-engineering-rules`](../fierro-engineering-rules/SKILL.md) — pillars and standards
- [`fierro-unblock`](../fierro-unblock/SKILL.md) — when the same error repeats
