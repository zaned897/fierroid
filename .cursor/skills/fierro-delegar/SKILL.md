---
name: fierro-delegar
description: "Delegate bounded tasks from Claude Code to OpenAI Codex or Google Antigravity (agy) in Fierro IoT: which tasks go to which agent, how scripts/delegar.py runs them in an isolated git worktree, how to review what comes back, and the optional Codex review Stop hook. Use when a task is small, self-contained and objectively checkable, when a second opinion on a diff would help, or when the user asks to involve Codex or Antigravity."
---

# Fierro delegar

Full guide: [`docs/agent/delegar.md`](../../../docs/agent/delegar.md)

## Central rule

> Claude owns the task and the PR. What Codex or agy return is someone else's diff:
> verify it, test it, then integrate or discard it.

## Who gets what

| Agent | Delegate | Keep away |
|-------|----------|-----------|
| Codex | Python/API work with a clear pass criterion, missing tests, mechanical refactors, scripts, diff review | Outbox, sync, idempotency, drivers |
| Antigravity | `apps/web` UI from an approved screen, visual tweaks, browser checks, long-document reading | Data contracts, device agent logic |
| Claude | Design, `apps/device-agent`, `event_id` idempotency, hardware boundary, integration, PRs | — |

Delegate only when the task fits in one paragraph, has an objective check (a test, a
screenshot) and does not touch the root invariant. When unsure, do not delegate.

## How

```bash
python scripts/delegar.py codex "<task>"
python scripts/delegar.py agy "<task>"            # --modo accept-edits|auto|plan
python scripts/delegar.py review                  # Codex second opinion vs main
```

1. The script makes a worktree under `.claude/worktrees/` on branch `delegar/...`
2. Read the summary in `.claude/delegaciones/` and `git -C <worktree> diff HEAD`
3. Run lint and tests in the worktree
4. Bring over what holds up (`git -C <worktree> diff HEAD --binary | git apply`), drop the rest
5. Remove the worktree and the `delegar/...` branch

The CLIs exist only on the user's PC. Exit code 2 means the CLI is missing, 4 means agy
was denied a permission in headless mode and did nothing. Say so, do the task yourself,
never pretend it was delegated.

## Codex review hook

`Stop` hook in `.claude/settings.json`, active only with `FIERRO_CODEX_REVIEW=1`. Reviews
each diff state once. Treat its findings as leads to verify, not as orders.
