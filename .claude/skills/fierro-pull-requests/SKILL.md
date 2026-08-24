---
name: fierro-pull-requests
description: "Branch naming, commits, PR creation, and merge conventions for fierroid. Use when creating or updating pull requests to main."
---

# Fierro pull requests

Full guide: [`docs/agent/pull-requests.md`](../../../docs/agent/pull-requests.md)

## When to use

- Creating a feature branch or opening a PR
- User asks to send work to main (prefer PR unless explicit direct push)

## Branch naming

```
cursor/<descriptive-kebab-name>-7dff
```

Base branch: **`main`**

```bash
git checkout main && git pull origin main
git checkout -b cursor/my-feature-7dff
```

## Before PR

```bash
source .venv/bin/activate
ruff check apps && pytest apps/device-agent apps/api -q
# if web changed: cd apps/web && pnpm lint && pnpm build
git push -u origin cursor/my-feature-7dff
```

## PR defaults

- Target: `main`
- Draft unless user wants ready for review
- Body: Summary, Test plan checklist, Jira key if any

## Do not

- Force push / amend unless asked
- Auto-merge PRs unless user explicitly requests
- Commit secrets, `.env`, `*.db`, `.venv`, `node_modules`

## Related

- [`docs/agent/testing.md`](../../../docs/agent/testing.md)
- [`docs/agent/jira.md`](../../../docs/agent/jira.md)
