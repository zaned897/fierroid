---
name: fierro-jira
description: "When and how to create or update Jira issues for Fierro IoT work: templates, duplicates, linking PRs, and Atlassian MCP. Use for bugs, stories, tasks, and sprint tracking."
---

# Fierro Jira workflow

Full guide: [`docs/agent/jira.md`](../../../docs/agent/jira.md)

## When to use

- User asks to open/create/file a Jira ticket
- Triage a bug (check duplicates first)
- Link PR work to sprint/epic
- Update ticket status after merge

## Workflow

1. **Search** for duplicate issues (summary, error text, component)
2. If duplicate → **comment** with new context or link PR
3. If new → create **Story / Task / Bug** with acceptance criteria
4. Implement on `cursor/*-7dff` branch → PR to `main` mentioning `FIERRO-XXX`
5. After merge → move ticket to Done (if Atlassian MCP authenticated)

## Issue templates (short)

**Story/Task summary:** `[component] Outcome`  
Example: `[device-agent] Read stable weight from RS232 scale`

**Bug summary:** `[bug] Symptom`  
Include: repro steps, expected vs actual, env (mock vs hardware)

## Atlassian MCP

If namespace `Atlassian` is available and authenticated:

- Discover tools via `GetDynamicTools` namespace `Atlassian`
- Search with JQL, create issue, add comments, transition status

If not authenticated: note in PR and ask user to create ticket or auth MCP in Cursor.

## Duplicate triage

Use Cursor **triage-issue** skill when investigating bugs and similar past issues.

## Project key

Replace placeholder **`FIERRO`** with the team's real Jira project key when configured.

## Related

- [`docs/agent/pull-requests.md`](../../../docs/agent/pull-requests.md)
- [`docs/agent/workflow.md`](../../../docs/agent/workflow.md)
