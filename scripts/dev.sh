#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if [[ ! -f .env ]]; then
  cp .env.example .env
  echo "Created .env from .env.example"
fi

if [[ ! -d .venv ]]; then
  python3 -m venv .venv
fi

# shellcheck disable=SC1091
source .venv/bin/activate
pip install -q -r backend/requirements.txt

cd backend
export PYTHONPATH=.
exec uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
# --reload: auto-restart after code changes
