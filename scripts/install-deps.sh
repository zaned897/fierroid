#!/usr/bin/env bash
# Idempotent dependency refresh for cloud agents / local bootstrap.
# Uses uv so we do not require apt package python3-venv on the base image.
set -euo pipefail
cd "$(dirname "$0")/.."

export PATH="${HOME}/.local/bin:${PATH}"

if ! command -v uv >/dev/null 2>&1; then
  curl -LsSf https://astral.sh/uv/install.sh | sh
  export PATH="${HOME}/.local/bin:${PATH}"
fi

if [[ ! -d .venv ]]; then
  uv venv .venv --python python3
fi

# shellcheck disable=SC1091
source .venv/bin/activate
uv pip install -e apps/device-agent -e apps/api -r requirements-dev.txt

if [[ -f apps/web/package.json ]]; then
  (cd apps/web && pnpm install)
fi
