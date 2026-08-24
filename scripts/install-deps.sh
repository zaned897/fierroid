#!/usr/bin/env bash
# Idempotent dependency refresh for cloud agents / local bootstrap.
set -euo pipefail
cd "$(dirname "$0")/.."

if [[ ! -d .venv ]]; then
  python3 -m venv .venv
fi
# shellcheck disable=SC1091
source .venv/bin/activate
pip install -q -U pip
pip install -q -e apps/device-agent -e apps/api -r requirements-dev.txt

if [[ -f apps/web/package.json ]]; then
  (cd apps/web && pnpm install)
fi
